import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from ticket_api.auth import Identity, TokenRejected

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer = HTTPBearer(auto_error=False, description="An access token from the identity provider.")


class NotSignedIn(Exception):
    """The request has no identity: no access token."""


class SignInUnavailable(Exception):
    """The API has no identity provider configured (OIDC_ISSUER is not set)."""


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
    """Who is calling: the checked access token of the request (Authorization: Bearer ...)."""
    validator = request.app.state.validator
    if validator is None:
        raise SignInUnavailable("OIDC_ISSUER is not set")
    if credentials is None:
        raise NotSignedIn("Send an access token: Authorization: Bearer <token>.")
    identity = validator.validate(credentials.credentials)  # raises TokenRejected
    request.state.identity = identity
    return identity


CurrentIdentity = Annotated[Identity, Depends(current_identity)]
__all__ = ["CurrentIdentity", "NotSignedIn", "SignInUnavailable", "TokenRejected"]
