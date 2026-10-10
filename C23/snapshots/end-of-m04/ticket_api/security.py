import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from ticket_api.auth import Identity, TokenRejected
from ticket_api.sessions import COOKIE, SessionEnded

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer = HTTPBearer(auto_error=False, description="An access token from the identity provider.")


class NotSignedIn(Exception):
    """The request has no identity: no access token."""


class SignInUnavailable(Exception):
    """The API has no identity provider configured (OIDC_ISSUER is not set)."""


class CsrfFailed(Exception):
    """A request that changes something came with the session cookie but without the
    session's CSRF token: another site may have started it."""


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def identity_from_cookie(request: Request, db, required: bool = True, csrf: bool = False):
    """The identity of the session cookie: (Identity, Session, row), or None (required=False).

    No database connection is held while the provider is asked for new tokens."""
    from ticket_api.login import is_expired, refresh_session

    value = request.cookies.get(COOKIE)
    if not value:
        if required:
            raise NotSignedIn("Sign in first.")
        return None
    sessions = request.app.state.sessions
    ended = None
    with db.connection() as conn:
        try:
            row = sessions.load(conn, value)
        except SessionEnded as error:
            ended = error  # raised after the block, so that the "ended" mark is committed
    if ended is None and csrf:
        sent = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(sent, row["csrf_token"]):
            raise CsrfFailed("This request needs the X-CSRF-Token header of your session.")
    if ended is None and is_expired(row["access_expires_at"]):
        if refresh_session(request, db, row) is None:
            with db.connection() as conn:
                sessions.end(conn, row["session_sha256"], "provider_refused")
            ended = SessionEnded("provider_refused")
    if ended is not None:
        if required:
            raise ended
        return None
    with db.connection() as conn:
        session = sessions.touch(conn, row)
    identity = Identity(
        user_id=row["user_id"],
        kind="user",
        client_id=request.app.state.settings.oidc_client_id,
        scopes=session.scopes,
        token_id=None,
        expires_at=session.expires_at,
        via="session",
    )
    request.state.identity = identity
    return identity, session, row


def require_api_key(
    request: Request, api_key: Annotated[str | None, Depends(api_key_header)]
) -> None:
    """Allow the request only with the API key from the server's settings."""
    expected = request.app.state.settings.api_key
    if expected is None:
        return
    if api_key is None or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=401, detail="A valid X-API-Key header is required."
        )


def current_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Identity:
    """Who is calling: the checked access token of the request (Authorization: Bearer ...),
    or else the browser's session cookie (Module 3). A request that changes something with
    the cookie must also send the session's CSRF token."""
    validator = request.app.state.validator
    if validator is None:
        raise SignInUnavailable("OIDC_ISSUER is not set")
    if credentials is not None:
        identity = validator.validate(credentials.credentials)  # raises TokenRejected
        request.state.identity = identity
        return identity
    if request.cookies.get(COOKIE) and request.app.state.db is not None:
        identity, _, _ = identity_from_cookie(
            request, request.app.state.db, csrf=request.method not in SAFE_METHODS
        )
        return identity
    raise NotSignedIn("Send an access token: Authorization: Bearer <token>.")


CurrentIdentity = Annotated[Identity, Depends(current_identity)]
__all__ = ["CurrentIdentity", "NotSignedIn", "SignInUnavailable", "TokenRejected"]
