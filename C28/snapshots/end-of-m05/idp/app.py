"""The provider's HTTP endpoints (Starlette): metadata, keys, client registration, sign-in, tokens."""

import base64
import csv
import hashlib
import html
import os
import secrets
import time
import urllib.parse

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

from idp import keys

SCOPES = ["knowledge:read", "tickets:read", "refunds:propose"]
# The resources (audiences) this provider issues tokens for: the MCP server's canonical URL.
RESOURCES = set(os.environ.get("IDP_RESOURCES", "http://127.0.0.1:8000/mcp http://localhost:8000/mcp").split())

_clients: dict[str, dict] = {
    "support-host": {
        "client_id": "support-host",
        "redirect_uris": ["http://127.0.0.1:8765/callback"],
        "client_name": "The course's host",
    }
}
_codes: dict[str, dict] = {}


def users() -> dict[str, str]:
    with (keys.ROOT / "data" / "users.csv").open(encoding="utf-8", newline="") as f:
        return {r["user_id"]: r["name"] for r in csv.DictReader(f)}


def error(code: str, description: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": code, "error_description": description}, status_code=status)


async def metadata(request: Request) -> JSONResponse:
    i = keys.ISSUER
    return JSONResponse(
        {
            "issuer": i,
            "authorization_endpoint": f"{i}/authorize",
            "token_endpoint": f"{i}/token",
            "registration_endpoint": f"{i}/register",
            "jwks_uri": f"{i}/jwks.json",
            "scopes_supported": SCOPES,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


async def jwks(request: Request) -> JSONResponse:
    return JSONResponse(keys.jwks())


async def register(request: Request) -> JSONResponse:
    """Dynamic client registration (RFC 7591), for public clients on this computer only."""
    body = await request.json()
    uris = body.get("redirect_uris") or []
    if not uris or not all(u.startswith(("http://127.0.0.1:", "http://localhost:")) for u in uris):
        return error("invalid_redirect_uri", "Redirect URIs must be on this computer (127.0.0.1 or localhost).")
    client_id = "client-" + secrets.token_hex(6)
    _clients[client_id] = {"client_id": client_id, "redirect_uris": uris, "client_name": body.get("client_name", "")}
    return JSONResponse(
        {**body, "client_id": client_id, "client_id_issued_at": int(time.time()), "token_endpoint_auth_method": "none"},
        status_code=201,
    )


async def authorize(request: Request):
    q = request.query_params
    client = _clients.get(q.get("client_id", ""))
    if client is None or q.get("redirect_uri") not in client["redirect_uris"]:
        return error("invalid_client", "Unknown client or redirect URI.")  # never redirect to an unknown URI
    if q.get("response_type") != "code" or q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
        return error("invalid_request", "This provider needs response_type=code and PKCE with S256.")
    resource = q.get("resource", "")
    if resource not in RESOURCES:
        return error("invalid_target", f"Unknown resource: {resource!r}.")
    scope = " ".join(s for s in q.get("scope", " ".join(SCOPES)).split() if s in SCOPES)
    user = q.get("login_hint") or q.get("user")
    if user not in users():  # the sign-in page: pick a made-up person (no password)
        links = "".join(
            f'<li><a href="/authorize?{html.escape(urllib.parse.urlencode({**q, "user": u}))}">{html.escape(n)} ({u})</a></li>'
            for u, n in users().items()
        )
        return HTMLResponse(f"<h1>Practice sign-in</h1><p>Made-up people only. Pick one:</p><ul>{links}</ul>")
    code = secrets.token_urlsafe(24)
    _codes[code] = {
        "client_id": client["client_id"],
        "redirect_uri": q["redirect_uri"],
        "user": user,
        "challenge": q["code_challenge"],
        "scope": scope,
        "resource": resource,
        "expires": time.time() + 60,
    }
    sep = "&" if "?" in q["redirect_uri"] else "?"
    params = {"code": code} | ({"state": q["state"]} if "state" in q else {}) | {"iss": keys.ISSUER}
    return RedirectResponse(f"{q['redirect_uri']}{sep}{urllib.parse.urlencode(params)}", status_code=302)


async def token(request: Request) -> JSONResponse:
    form = await request.form()
    if form.get("grant_type") != "authorization_code":
        return error("unsupported_grant_type", "Only authorization_code.")
    c = _codes.pop(form.get("code", ""), None)  # a code works once
    if c is None or c["expires"] < time.time():
        return error("invalid_grant", "Unknown, used or expired code.")
    if form.get("client_id") != c["client_id"] or form.get("redirect_uri") != c["redirect_uri"]:
        return error("invalid_grant", "The code was issued to another client or redirect URI.")
    verifier = form.get("code_verifier", "")
    if not 43 <= len(verifier) <= 128:
        return error("invalid_grant", "The code verifier must have 43 to 128 characters (RFC 7636).")
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    if digest != c["challenge"]:
        return error("invalid_grant", "Invalid code verifier.")
    if form.get("resource", c["resource"]) != c["resource"]:
        return error("invalid_target", "The resource differs from the one in the authorization request.")
    at = keys.access_token(c["user"], c["scope"], c["resource"], client_id=c["client_id"])
    return JSONResponse(
        {"access_token": at, "token_type": "Bearer", "expires_in": keys.ACCESS_TOKEN_SECONDS, "scope": c["scope"]},
        headers={"Cache-Control": "no-store"},
    )


app = Starlette(
    routes=[
        Route("/.well-known/oauth-authorization-server", metadata),
        Route("/.well-known/openid-configuration", metadata),
        Route("/jwks.json", jwks),
        Route("/register", register, methods=["POST"]),
        Route("/authorize", authorize),
        Route("/token", token, methods=["POST"]),
    ]
)
