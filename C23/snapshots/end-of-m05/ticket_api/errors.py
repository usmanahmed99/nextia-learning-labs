import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ticket_api.admin import NotPlatformAdmin
from ticket_api.auth import ProviderUnavailable, TokenRejected
from ticket_api.classifier import ClassifierUnavailable
from ticket_api.db import DatabaseBusy, DatabaseUnavailable
from ticket_api.history import HistoryUnavailable
from ticket_api.login import LoginFailed
from ticket_api.models import ErrorDetail, ErrorResponse
from ticket_api.repository import Conflict, InvalidCursor, NotFound
from ticket_api.security import CsrfFailed, NotSignedIn, SignInUnavailable
from ticket_api.sessions import COOKIE, SessionEnded
from ticket_api.tenancy import AccessDenied

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
    return JSONResponse(status_code=status, content=ErrorResponse(error=detail).model_dump())


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        fields = [field_name(e) for e in exc.errors()]
        return error_response(request, 422, "invalid_request", "The request is not valid.", fields)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = CODES.get(exc.status_code, "http_error")
        return error_response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(ClassifierUnavailable)
    async def classifier_unavailable(request: Request, exc: ClassifierUnavailable):
        logger.warning("classifier unavailable: %s id=%s", exc, request.state.request_id)
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

    # ---------- sign-in (the authentication course) ----------

    @app.exception_handler(NotSignedIn)
    async def not_signed_in(request: Request, exc: NotSignedIn):
        response = error_response(request, 401, "not_signed_in", str(exc))
        response.headers["WWW-Authenticate"] = 'Bearer realm="ticket-api"'
        return response

    @app.exception_handler(TokenRejected)
    async def token_rejected(request: Request, exc: TokenRejected):
        logger.info("token rejected: %s id=%s", exc.code, request.state.request_id)
        response = error_response(request, 401, "invalid_token", str(exc))
        response.headers["WWW-Authenticate"] = (
            f'Bearer realm="ticket-api", error="invalid_token", error_description="{exc}"'
        )
        response.headers["X-Token-Check"] = exc.code  # which check refused it
        return response

    @app.exception_handler(NotPlatformAdmin)
    async def not_platform_admin(request: Request, exc: NotPlatformAdmin):
        return error_response(request, 403, "forbidden", str(exc))

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict):
        return error_response(request, 409, exc.code, str(exc))

    @app.exception_handler(AccessDenied)
    async def access_denied(request: Request, exc: AccessDenied):
        d = exc.decision
        logger.info(
            "access denied: %s %s %s in %s id=%s",
            d.code,
            getattr(getattr(request.state, "identity", None), "user_id", "?"),
            exc.action,
            exc.tenant_id,
            request.state.request_id,
        )
        if d.status == 404:
            # The same answer as for an organization that does not exist: an outsider
            # learns nothing.
            return error_response(request, 404, "not_found", "Not found.")
        if d.code == "missing_scope":
            response = error_response(
                request, 403, "insufficient_scope", d.rule[0].upper() + d.rule[1:] + "."
            )
            response.headers["WWW-Authenticate"] = (
                'Bearer realm="ticket-api", error="insufficient_scope"'
            )
            return response
        return error_response(request, 403, "forbidden", f"Your role may not do this ({d.rule}).")

    @app.exception_handler(SessionEnded)
    async def session_ended(request: Request, exc: SessionEnded):
        response = error_response(
            request, 401, "session_ended", f"Your session has ended ({exc.reason}). Sign in again."
        )
        response.delete_cookie(COOKIE, path="/")
        return response

    @app.exception_handler(CsrfFailed)
    async def csrf_failed(request: Request, exc: CsrfFailed):
        return error_response(request, 403, "csrf_failed", str(exc))

    @app.exception_handler(LoginFailed)
    async def login_failed(request: Request, exc: LoginFailed):
        logger.info("sign-in failed: %s id=%s", exc, request.state.request_id)
        return error_response(request, 400, "login_failed", str(exc))

    @app.exception_handler(SignInUnavailable)
    async def sign_in_unavailable(request: Request, exc: SignInUnavailable):
        return error_response(
            request, 503, "sign_in_unavailable", "Sign-in is not set up on this server."
        )

    @app.exception_handler(ProviderUnavailable)
    async def provider_unavailable(request: Request, exc: ProviderUnavailable):
        logger.warning("identity provider unavailable: %s id=%s", exc, request.state.request_id)
        return error_response(
            request,
            503,
            "identity_provider_unavailable",
            "The identity provider does not answer. Try again later.",
        )

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        logger.exception("unexpected error id=%s", request.state.request_id)
        return error_response(request, 500, "internal_error", "Something went wrong on the server.")
