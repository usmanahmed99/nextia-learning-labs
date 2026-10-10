"""Browser sign-in through the API (a "backend for frontend"), the authentication course, Module 3.

GET  /auth/login?return_to=/app/   start: PKCE, state and nonce are kept here; go to the provider
GET  /auth/callback                the provider sends the browser back with a code: swap it for
                                   tokens (with the client secret), check the ID token, start a
                                   session, set the HttpOnly cookie
GET  /auth/session                 is this browser signed in? (and its CSRF token)
POST /auth/logout                  end the session, revoke the refresh token, clear the cookie
GET  /app/                         a small page that uses all of this

The tokens never reach the browser: JavaScript cannot read the cookie (HttpOnly), and a
script injected into the page finds no token to steal.
"""

import base64
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ticket_api import repository
from ticket_api.auth import ProviderConfig, TokenRejected, check_id_token
from ticket_api.db import Database
from ticket_api.sessions import COOKIE, SessionStore
from ticket_api.tickets import DB

logger = logging.getLogger("ticket_api")

router = APIRouter(tags=["sign-in"])
APP_PAGE = Path(__file__).parent / "static" / "app.html"
SCOPE = "openid profile email offline_access tickets:read tickets:write members:manage"


class LoginFailed(Exception):
    """The sign-in could not finish (a wrong or old state, a refused code, a bad ID token)."""


def safe_return_to(value: str | None) -> str:
    """Only a path on this site: never another site (an open redirect sends people anywhere)."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return "/app/"


def provider_of(request: Request) -> ProviderConfig:
    validator = request.app.state.validator
    if validator is None or not request.app.state.settings.oidc_client_id:
        from ticket_api.security import SignInUnavailable

        raise SignInUnavailable("OIDC_ISSUER or OIDC_CLIENT_ID is not set")
    return validator.provider


def store_of(request: Request) -> SessionStore:
    return request.app.state.sessions


def client_auth(request: Request) -> tuple[str, str]:
    s = request.app.state.settings
    return (s.oidc_client_id, s.oidc_client_secret or "")


def set_cookie(request: Request, response, value: str, max_age: int) -> None:
    response.set_cookie(
        COOKIE,
        value,
        max_age=max_age,
        httponly=True,  # JavaScript cannot read it
        secure=request.app.state.settings.session_cookie_secure,  # HTTPS only (not on 127.0.0.1)
        samesite="lax",  # not sent with requests that other sites start, except top-level links
        path="/",
    )


@router.get("/auth/login", summary="Sign in with the identity provider")
def login(
    request: Request,
    db: DB,
    return_to: str | None = None,
    prompt: Annotated[str | None, Query(pattern="^(login|select_account)$")] = None,
) -> RedirectResponse:
    provider = provider_of(request)
    with db.connection() as conn:
        state, nonce, verifier = store_of(request).start_login(conn, safe_return_to(return_to))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    params = {
        "response_type": "code",
        "client_id": request.app.state.settings.oidc_client_id,
        "redirect_uri": request.app.state.settings.oidc_redirect_uri,
        "scope": SCOPE,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge.decode().rstrip("="),
        "code_challenge_method": "S256",
    }
    if prompt:
        params["prompt"] = prompt  # select_account: show the list again (account switching)
    authorize = provider.discovery()["authorization_endpoint"]
    return RedirectResponse(f"{authorize}?{urlencode(params)}", status_code=302)


@router.get("/auth/callback", summary="The provider sends the browser back here")
def callback(
    request: Request,
    db: DB,
    state: str = "",
    code: str = "",
    error: str | None = None,
) -> RedirectResponse:
    settings = request.app.state.settings
    provider, sessions = provider_of(request), store_of(request)
    with db.connection() as conn:
        waiting = sessions.finish_login(conn, state) if state else None
    if waiting is None:
        raise LoginFailed("This sign-in is unknown, was used already, or is too old. Start again.")
    if error:
        raise LoginFailed(f"The identity provider refused the sign-in: {error}.")
    # The code goes back to the provider with the PKCE verifier and our client secret
    # (no database connection is held during the call).
    status, body = provider.post(
        provider.endpoint("token_endpoint"),
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.oidc_redirect_uri,
            "code_verifier": waiting["code_verifier"],
        },
        client_auth(request),
    )
    if status != 200:
        raise LoginFailed(f"The provider refused the code: {body.get('error', status)}.")
    try:
        id_claims = check_id_token(
            provider, body.get("id_token", ""), settings.oidc_client_id, waiting["nonce"]
        )
        identity = request.app.state.validator.validate(body["access_token"])
    except TokenRejected as rejected:
        raise LoginFailed(f"The tokens are not valid: {rejected}") from None
    if identity.user_id != id_claims["sub"]:
        raise LoginFailed("The ID token and the access token are for different people.")
    with db.connection() as conn:
        repository.upsert_user(
            conn, id_claims["sub"], id_claims.get("name"), id_claims.get("email")
        )
        value = sessions.create(
            conn,
            identity.user_id,
            " ".join(sorted(identity.scopes)),
            body.get("refresh_token"),
            identity.expires_at,
        )
    response = RedirectResponse(waiting["return_to"], status_code=302)
    set_cookie(request, response, value, int(sessions.max.total_seconds()))
    logger.info("signed in user=%s", identity.user_id)
    return response


@router.get("/auth/session", summary="Is this browser signed in?")
def session_info(request: Request, db: DB) -> JSONResponse:
    from ticket_api.security import identity_from_cookie

    found = identity_from_cookie(request, db, required=False)
    if found is None:
        return JSONResponse({"signed_in": False}, headers={"Cache-Control": "no-store"})
    identity, session, _ = found
    return JSONResponse(
        {
            "signed_in": True,
            "user_id": identity.user_id,
            "csrf_token": session.csrf_token,
            "expires_at": session.expires_at.isoformat(),
            "idle_expires_at": session.idle_expires_at.isoformat(),
        },
        headers={"Cache-Control": "no-store"},
    )


@router.post("/auth/logout", summary="Sign out")
def logout(request: Request, db: DB) -> JSONResponse:
    """End this session here and at the provider. Needs the X-CSRF-Token header: another site
    cannot sign you out (or in) behind your back."""
    from ticket_api.security import identity_from_cookie

    provider, sessions = provider_of(request), store_of(request)
    _, session, row = identity_from_cookie(request, db, required=True, csrf=True)
    with db.connection() as conn:
        sessions.end(conn, session.session_sha256, "logout")
    refresh = sessions.refresh_token(row)
    if refresh:  # the provider forgets the refresh token: it cannot make new access tokens
        provider.post(
            provider.endpoint("revocation_endpoint"),
            {"token": refresh, "token_type_hint": "refresh_token"},
            client_auth(request),
        )
    end_session = provider.discovery().get("end_session_endpoint")
    after = request.app.state.settings.post_logout_redirect_uri
    body = {
        "signed_out": True,
        # Also sign out at the provider, or the next sign-in there is silent (same person).
        "provider_logout_url": f"{end_session}?{urlencode({'post_logout_redirect_uri': after})}",
    }
    response = JSONResponse(body, headers={"Cache-Control": "no-store"})
    response.delete_cookie(COOKIE, path="/")
    return response


@router.get("/app/", include_in_schema=False)
def app_page() -> HTMLResponse:
    return HTMLResponse(APP_PAGE.read_text(encoding="utf-8"), headers={"Cache-Control": "no-store"})


def refresh_session(request: Request, db: Database, row: dict) -> datetime | None:
    """The access token's time is over: ask the provider for new tokens with the refresh token.
    Returns the new access expiry, or None if the provider said no (the session then ends)."""
    provider, sessions = request.app.state.validator.provider, request.app.state.sessions
    refresh = sessions.refresh_token(row)
    if refresh is None:
        return None
    status, body = provider.post(
        provider.endpoint("token_endpoint"),
        {"grant_type": "refresh_token", "refresh_token": refresh},
        client_auth(request),
    )
    if status != 200:
        logger.info("refresh refused for user=%s: %s", row["user_id"], body.get("error"))
        return None
    try:
        identity = request.app.state.validator.validate(body["access_token"])
    except TokenRejected:
        return None
    expires = identity.expires_at
    with db.connection() as conn:
        sessions.renewed(conn, row, body.get("refresh_token", refresh), expires)
    return expires


def is_expired(at: datetime) -> bool:
    return datetime.now(UTC) >= at - timedelta(seconds=5)
