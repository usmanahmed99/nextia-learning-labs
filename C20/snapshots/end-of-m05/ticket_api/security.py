import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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
