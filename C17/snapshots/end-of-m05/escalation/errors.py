"""One error shape for every failure, as in the ticket API:
{"error": {"code": ..., "message": ..., "request_id": ..., "fields": [...]}}"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

logger = logging.getLogger("escalation")

CODES = {401: "unauthorized", 404: "not_found", 405: "method_not_allowed", 429: "too_many_jobs"}


class ErrorDetail(BaseModel):
    code: str = Field(description="A stable code that a program can check.")
    message: str = Field(description="A short explanation for a person.")
    request_id: str | None = None
    fields: list[str] = []


class ErrorResponse(BaseModel):
    error: ErrorDetail


def field_name(error: dict) -> str:
    if error["type"] == "json_invalid":
        return "body"
    return ".".join(str(part) for part in error["loc"][1:]) or "body"


def error_response(request: Request, status: int, code: str, message: str, fields=()) -> JSONResponse:
    detail = ErrorDetail(
        code=code,
        message=message,
        request_id=getattr(request.state, "request_id", None),
        fields=list(fields),
    )
    return JSONResponse(status_code=status, content=ErrorResponse(error=detail).model_dump())


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        fields = sorted({field_name(e) for e in exc.errors()})
        request.app.state.monitor.contract_error(fields)
        return error_response(
            request, 422, "invalid_ticket", "The ticket does not match the model's contract.", fields
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = CODES.get(exc.status_code, "http_error")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("unexpected error id=%s", getattr(request.state, "request_id", None))
        return error_response(request, 500, "internal_error", "Something went wrong on the server.")
