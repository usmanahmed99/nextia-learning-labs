import logging
import math

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ticket_api.ai import BadAnswer
from ticket_api.classifier import ClassifierUnavailable
from ticket_api.db import DatabaseBusy, DatabaseUnavailable
from ticket_api.history import HistoryUnavailable
from ticket_api.models import ErrorDetail, ErrorResponse
from ticket_api.provider import ProviderError, ProviderRateLimited, ProviderRejected
from ticket_api.repository import InvalidCursor, NotFound

logger = logging.getLogger("ticket_api")

class FilesUnavailable(Exception):
    """File storage is off, or it does not answer."""


class UploadRejected(Exception):
    """An uploaded file breaks a rule (too large, missing, another size)."""

    def __init__(self, message: str, code: str = "upload_rejected", status: int = 422):
        super().__init__(message)
        self.code = code
        self.status = status


CODES = {401: "unauthorized", 404: "not_found", 405: "method_not_allowed"}


def field_name(error: dict) -> str:
    """Return the field that a validation error is about, such as "subject"."""
    if error["type"] == "json_invalid":
        return "body"
    return ".".join(str(part) for part in error["loc"][1:]) or "body"


def error_response(
    request: Request, status: int, code: str, message: str, fields=()
) -> JSONResponse:
    detail = ErrorDetail(
        code=code,
        message=message,
        request_id=getattr(request.state, "request_id", None),
        fields=list(fields),
    )
    return JSONResponse(
        status_code=status, content=ErrorResponse(error=detail).model_dump()
    )


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        fields = [field_name(e) for e in exc.errors()]
        return error_response(
            request, 422, "invalid_request", "The request is not valid.", fields
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = CODES.get(exc.status_code, "http_error")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(ClassifierUnavailable)
    async def classifier_unavailable(request: Request, exc: ClassifierUnavailable):
        logger.warning(
            "classifier unavailable: %s id=%s", exc, request.state.request_id
        )
        return error_response(
            request,
            503,
            "classifier_unavailable",
            "The classifier is not available. Try again later.",
        )

    @app.exception_handler(HistoryUnavailable)
    async def history_unavailable(request: Request, exc: HistoryUnavailable):
        logger.warning("history unavailable: %s id=%s", exc, request.state.request_id)
        return error_response(
            request,
            503,
            "history_unavailable",
            "The history is not available. Try again later.",
        )

    @app.exception_handler(DatabaseUnavailable)
    async def database_unavailable(request: Request, exc: DatabaseUnavailable):
        logger.warning("database unavailable: %s id=%s", exc, request.state.request_id)
        return error_response(
            request, 503, "database_unavailable", "The database is not available. Try again later."
        )

    @app.exception_handler(DatabaseBusy)
    async def database_busy(request: Request, exc: DatabaseBusy):
        logger.warning("database busy: %s id=%s", exc, request.state.request_id)
        response = error_response(
            request, 503, "database_busy", "The database is busy. Try again in a few seconds."
        )
        response.headers["Retry-After"] = "2"
        return response

    @app.exception_handler(NotFound)
    async def not_found(request: Request, exc: NotFound):
        return error_response(request, 404, "not_found", str(exc))

    @app.exception_handler(InvalidCursor)
    async def invalid_cursor(request: Request, exc: InvalidCursor):
        return error_response(
            request, 422, "invalid_request", "The value of after is not valid.", ["after"]
        )

    @app.exception_handler(FilesUnavailable)
    async def files_unavailable(request: Request, exc: FilesUnavailable):
        return error_response(request, 503, "files_unavailable", str(exc))

    @app.exception_handler(UploadRejected)
    async def upload_rejected(request: Request, exc: UploadRejected):
        return error_response(request, exc.status, exc.code, str(exc))

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError):
        logger.warning("AI provider: %s id=%s", exc, request.state.request_id)
        if isinstance(exc, ProviderRateLimited):
            wait = max(1, math.ceil(exc.retry_after or 5))
            response = error_response(
                request, 503, "ai_busy", f"The AI provider is busy. Try again in {wait} seconds."
            )
            response.headers["Retry-After"] = str(wait)
            return response
        if isinstance(exc, ProviderRejected):
            return error_response(
                request, 502, "ai_bad_answer", "The AI provider refused the request."
            )
        return error_response(
            request, 503, "ai_unavailable", "The AI provider is not available. Try again later."
        )

    @app.exception_handler(BadAnswer)
    async def bad_answer(request: Request, exc: BadAnswer):
        logger.warning("AI provider: %s id=%s", exc, request.state.request_id)
        return error_response(
            request, 502, "ai_bad_answer", "The AI provider gave an answer that is not valid."
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("unexpected error id=%s", request.state.request_id)
        return error_response(
            request, 500, "internal_error", "Something went wrong on the server."
        )
