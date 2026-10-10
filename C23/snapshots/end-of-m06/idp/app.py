"""The provider's endpoints (OpenID Connect, the parts the course uses).

GET  /.well-known/openid-configuration   where everything is (discovery)
GET  /jwks.json                          the public keys that check the signatures
GET  /authorize                          the sign-in page (pick a made-up person)
POST /authorize                          the person chose: redirect back with a one-time code
POST /token                              code + PKCE verifier -> tokens; refresh; client credentials
POST /revoke                             end a refresh token (and its family)
GET  /userinfo                           who the access token is for
GET  /logout                             end the provider's own sign-in session
"""

import base64
import hashlib
import html
import re
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

import jwt
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from idp.store import Store, sha256
from idp.tokens import Signer

CODE_SECONDS = 60
VERIFIER = re.compile(r"[A-Za-z0-9\-._~]{43,128}")  # RFC 7636, section 4.1
SESSION_COOKIE = "idp_session"


@dataclass
class Code:
    client_id: str
    redirect_uri: str
    sub: str
    scope: str
    nonce: str | None
    challenge: str
    auth_time: int
    expires: float
    used: bool = False


@dataclass
class Refresh:
    family: str
    client_id: str
    sub: str
    scope: str
    auth_time: int
    expires: float
    used: bool = False


@dataclass
class State:
    codes: dict[str, Code] = field(default_factory=dict)
    refresh: dict[str, Refresh] = field(default_factory=dict)  # by SHA-256 of the token
    revoked_families: set[str] = field(default_factory=set)
    sessions: dict[str, tuple[str, int]] = field(default_factory=dict)  # id -> (sub, auth time)


class OAuthError(Exception):
    def __init__(self, error: str, description: str, status: int = 400):
        super().__init__(description)
        self.error, self.description, self.status = error, description, status


def s256(verifier: str) -> str:
    """PKCE's S256: BASE64URL(SHA-256(verifier)), without padding (RFC 7636)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def create_app(
    store: Store | None = None,
    issuer: str = "http://localhost:8400",
    access_seconds: int = 600,
    refresh_seconds: int = 8 * 3600,
    clock=time.time,
) -> FastAPI:
    store = store or Store()
    if not store.exists():
        raise SystemExit("The provider has no keys yet. Run: python -m idp init")
    signer = Signer(store, issuer, access_seconds=access_seconds)
    state = State()
    app = FastAPI(title="Mock identity provider (practice only)", docs_url=None, redoc_url=None)
    app.state.store, app.state.signer = store, signer
    app.state.oauth, app.state.clock = state, clock

    @app.exception_handler(OAuthError)
    async def oauth_error(request: Request, exc: OAuthError):
        return JSONResponse(
            {"error": exc.error, "error_description": exc.description},
            status_code=exc.status,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/.well-known/openid-configuration")
    def discovery():
        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "userinfo_endpoint": f"{issuer}/userinfo",
            "jwks_uri": f"{issuer}/jwks.json",
            "revocation_endpoint": f"{issuer}/revoke",
            "end_session_endpoint": f"{issuer}/logout",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token", "client_credentials"],
            "code_challenge_methods_supported": ["S256"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "scopes_supported": [
                "openid",
                "profile",
                "email",
                "offline_access",
                "tickets:read",
                "tickets:write",
                "members:manage",
            ],
            "token_endpoint_auth_methods_supported": [
                "client_secret_post",
                "client_secret_basic",
                "none",
            ],
        }

    @app.get("/jwks.json")
    def jwks():
        return store.jwks()

    # ---------- sign in ----------

    def check_request(params) -> tuple[dict, list[str]]:
        """The checks before anything is shown. An unknown client or redirect URI is an error
        page, never a redirect: the provider sends codes only to registered addresses."""
        client = store.clients().get(params.get("client_id", ""))
        if client is None or "authorization_code" not in client["grant_types"]:
            raise OAuthError("invalid_client", "This application is not registered.")
        if params.get("redirect_uri") not in client["redirect_uris"]:
            raise OAuthError(
                "invalid_request", "This redirect URI is not registered for the application."
            )
        if params.get("response_type") != "code":
            raise OAuthError("unsupported_response_type", "Only response_type=code is supported.")
        if params.get("code_challenge_method") != "S256" or not params.get("code_challenge"):
            raise OAuthError(
                "invalid_request",
                "PKCE is required: send code_challenge and code_challenge_method=S256.",
            )
        if not params.get("state"):
            raise OAuthError("invalid_request", "Send a state value.")
        scopes = params.get("scope", "").split()
        unknown = [s for s in scopes if s not in client["scopes"]]
        if "openid" not in scopes or unknown:
            raise OAuthError(
                "invalid_scope",
                f"Scopes not allowed for this application: "
                f"{' '.join(unknown) or 'openid is missing'}",
            )
        return client, scopes

    def issue_code(params, sub: str, auth_time: int) -> RedirectResponse:
        code = secrets.token_urlsafe(32)
        state.codes[code] = Code(
            client_id=params["client_id"],
            redirect_uri=params["redirect_uri"],
            sub=sub,
            scope=params["scope"],
            nonce=params.get("nonce"),
            challenge=params["code_challenge"],
            auth_time=auth_time,
            expires=clock() + CODE_SECONDS,
        )
        query = urlencode({"code": code, "state": params["state"]})
        return RedirectResponse(f"{params['redirect_uri']}?{query}", status_code=302)

    @app.get("/authorize")
    def authorize(request: Request):
        params = dict(request.query_params)
        client, _ = check_request(params)
        session = state.sessions.get(request.cookies.get(SESSION_COOKIE, ""))
        if session and params.get("prompt") not in ("login", "select_account"):
            user = store.users().get(session[0])
            if user and not user["disabled"]:
                return issue_code(params, *session)  # already signed in at the provider
        return HTMLResponse(picker(client, params, store.users()))

    @app.post("/authorize")
    def choose(request: Request, user: str = Form(...)):
        params = {k: v for k, v in request.query_params.items()}
        check_request(params)
        person = store.users().get(user)
        if person is None or person["disabled"]:
            raise OAuthError("access_denied", "This account cannot sign in.", 403)
        auth_time = int(clock())
        response = issue_code(params, user, auth_time)
        sid = secrets.token_urlsafe(24)
        state.sessions[sid] = (user, auth_time)
        response.set_cookie(SESSION_COOKIE, sid, httponly=True, samesite="lax", path="/")
        return response

    @app.get("/logout")
    def logout(request: Request, post_logout_redirect_uri: str = "", client_id: str = ""):
        state.sessions.pop(request.cookies.get(SESSION_COOKIE, ""), None)
        allowed = [u for c in store.clients().values() for u in c["post_logout_redirect_uris"]]
        if post_logout_redirect_uri in allowed:
            response = RedirectResponse(post_logout_redirect_uri, status_code=302)
        else:
            response = HTMLResponse("<p>You are signed out of the practice identity provider.</p>")
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    # ---------- tokens ----------

    def client_auth(request: Request, form: dict) -> dict:
        client_id, secret = form.get("client_id", ""), form.get("client_secret")
        header = request.headers.get("authorization", "")
        if header.lower().startswith("basic "):
            try:
                client_id, secret = base64.b64decode(header[6:]).decode().split(":", 1)
            except ValueError:
                raise OAuthError(
                    "invalid_client", "The client authentication is not valid.", 401
                ) from None
        client = store.clients().get(client_id)
        if client is None:
            raise OAuthError("invalid_client", "This application is not registered.", 401)
        if client["type"] == "confidential":
            if not secret or not secrets.compare_digest(sha256(secret), client["secret_sha256"]):
                raise OAuthError("invalid_client", "The client secret is wrong.", 401)
        return client

    def token_response(
        client: dict,
        sub: str,
        scope: str,
        auth_time: int,
        nonce: str | None = None,
        family: str | None = None,
    ) -> JSONResponse:
        scopes = scope.split()
        api_scope = " ".join(s for s in scopes if ":" in s)
        body = {
            "access_token": signer.access_token(sub, client["client_id"], api_scope, now=clock()),
            "token_type": "Bearer",
            "expires_in": signer.access_seconds,
            "scope": scope,
        }
        if "openid" in scopes:
            user = store.users()[sub]
            body["id_token"] = signer.id_token(
                user, client["client_id"], nonce, auth_time, now=clock()
            )
        if "offline_access" in scopes:
            token = secrets.token_urlsafe(32)
            state.refresh[sha256(token)] = Refresh(
                family=family or secrets.token_hex(8),
                client_id=client["client_id"],
                sub=sub,
                scope=scope,
                auth_time=auth_time,
                expires=clock() + refresh_seconds,
            )
            body["refresh_token"] = token
        return JSONResponse(body, headers={"Cache-Control": "no-store"})

    @app.post("/token")
    async def token(request: Request):
        form = dict(await request.form())
        client = client_auth(request, form)
        grant = form.get("grant_type")
        if grant not in client["grant_types"]:
            raise OAuthError("unauthorized_client", f"This application may not use {grant}.")
        if grant == "authorization_code":
            code = state.codes.get(form.get("code", ""))
            if code is None or code.used or code.expires < clock():
                raise OAuthError("invalid_grant", "The code is not valid, was used, or expired.")
            code.used = True  # one use only
            if code.client_id != client["client_id"] or code.redirect_uri != form.get(
                "redirect_uri"
            ):
                raise OAuthError(
                    "invalid_grant", "The code was issued to another application or redirect URI."
                )
            verifier = form.get("code_verifier", "")
            if not VERIFIER.fullmatch(verifier):
                raise OAuthError(
                    "invalid_grant",
                    "The code_verifier must have 43 to 128 characters (A-Z a-z 0-9 - . _ ~).",
                )
            if s256(verifier) != code.challenge:
                raise OAuthError(
                    "invalid_grant", "The PKCE code_verifier does not match the code_challenge."
                )
            return token_response(client, code.sub, code.scope, code.auth_time, code.nonce)
        if grant == "refresh_token":
            key = sha256(form.get("refresh_token", ""))
            old = state.refresh.get(key)
            if old is None or old.client_id != client["client_id"]:
                raise OAuthError("invalid_grant", "The refresh token is not valid.")
            if old.used or old.family in state.revoked_families:
                # A used refresh token came back: someone may have a copy. End the family.
                state.revoked_families.add(old.family)
                raise OAuthError("invalid_grant", "The refresh token was already used or revoked.")
            if old.expires < clock():
                raise OAuthError("invalid_grant", "The refresh token has expired.")
            user = store.users().get(old.sub)
            if user is None or user["disabled"]:
                state.revoked_families.add(old.family)
                raise OAuthError("invalid_grant", "This account cannot sign in any more.")
            old.used = True  # rotation: every refresh token works once
            return token_response(client, old.sub, old.scope, old.auth_time, family=old.family)
        if grant == "client_credentials":
            wanted = form.get("scope", " ".join(client["scopes"])).split()
            if any(s not in client["scopes"] for s in wanted):
                raise OAuthError("invalid_scope", "A scope is not allowed for this application.")
            access = signer.access_token(
                client["client_id"], client["client_id"], " ".join(wanted), now=clock()
            )
            return JSONResponse(
                {
                    "access_token": access,
                    "token_type": "Bearer",
                    "expires_in": signer.access_seconds,
                    "scope": " ".join(wanted),
                },
                headers={"Cache-Control": "no-store"},
            )
        raise OAuthError("unsupported_grant_type", f"Unknown grant_type {grant!r}.")

    @app.post("/revoke")
    async def revoke(request: Request):
        form = dict(await request.form())
        client_auth(request, form)
        old = state.refresh.get(sha256(form.get("token", "")))
        if old is not None:
            state.revoked_families.add(old.family)
        return JSONResponse({}, status_code=200)  # RFC 7009: the same answer for unknown tokens

    @app.get("/userinfo")
    def userinfo(request: Request):
        header = request.headers.get("authorization", "")
        try:
            kid = jwt.get_unverified_header(header[7:])["kid"]
            claims = jwt.decode(
                header[7:],
                jwt.PyJWK({**next(k for k in store.jwks()["keys"] if k["kid"] == kid)}).key,
                algorithms=["RS256"],
                audience=signer.audience,
                issuer=issuer,
            )
        except Exception:
            raise OAuthError("invalid_token", "A valid access token is required.", 401) from None
        user = store.users().get(claims["sub"])
        if user is None:
            raise OAuthError("invalid_token", "This token is not for a person.", 401)
        return {"sub": user["sub"], "name": user["name"], "email": user["email"]}

    return app


def picker(client: dict, params: dict, users: dict) -> str:
    """The sign-in page. A real provider asks for a password (and often a second factor); this
    practice provider lets you pick a made-up person."""
    rows = "".join(
        f'<li><button name="user" value="{html.escape(u["sub"])}"'
        f"{' disabled' if u['disabled'] else ''}>{html.escape(u['name'])}</button> "
        f"<small>{html.escape(u['email'])}{' (disabled)' if u['disabled'] else ''}</small></li>"
        for u in users.values()
    )
    action = "/authorize?" + urlencode(params)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Sign in (practice)</title>"
        "<style>body{font-family:system-ui;max-width:32rem;margin:3rem auto}"
        "li{list-style:none;margin:.5rem 0}button{min-width:7rem}</style></head><body>"
        f"<h1>Sign in to {html.escape(client['name'])}</h1>"
        "<p>This is the course's <strong>practice identity provider</strong>. It does not ask "
        "for a password: pick a made-up person.</p>"
        f"<p>The application asks for: <code>{html.escape(params.get('scope', ''))}</code></p>"
        f"<form method='post' action='{html.escape(action)}'><ul>{rows}</ul></form>"
        "</body></html>"
    )
