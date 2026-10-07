import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ticket_api.classifier import ClassifierUnavailable
from ticket_api.history import HistoryUnavailable
from ticket_api.models import ErrorDetail, ErrorResponse

logger = logging.getLogger("ticket_api")

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

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("unexpected error id=%s", request.state.request_id)
        return error_response(
            request, 500, "internal_error", "Something went wrong on the server."
        )
