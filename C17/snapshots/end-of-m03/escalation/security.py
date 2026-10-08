import secrets

from fastapi import Request
from fastapi.security import APIKeyHeader
from starlette.exceptions import HTTPException

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(request: Request) -> None:
    """Allow the request only with the right X-API-Key, if a key is set."""
    expected = request.app.state.settings.api_key
    if expected is None:
        return
    given = request.headers.get("X-API-Key") or ""
    if not secrets.compare_digest(given.encode(), expected.encode()):
        raise HTTPException(401, "A valid X-API-Key header is required.")
