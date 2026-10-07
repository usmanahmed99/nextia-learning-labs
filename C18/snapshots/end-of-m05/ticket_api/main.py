import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ticket_api.classifier import make_classifier
from ticket_api.config import Settings, SettingsError, load_settings
from ticket_api.errors import add_error_handlers, error_response
from ticket_api.history import History, HistoryUnavailable
from ticket_api.models import ErrorResponse, Health, Readiness
from ticket_api.routes import router

MAX_BODY_BYTES = 16_384

logger = logging.getLogger("ticket_api")

DESCRIPTION = """
Classifies support tickets into a category and a priority.

The classifier is a deterministic mock: it uses keywords, so the same text
always gives the same result. Every error has the same shape:
`{"error": {"code": ..., "message": ..., "request_id": ..., "fields": [...]}}`.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
    )

    app = FastAPI(
        title="Ticket Classifier API",
        version="1.1.0",
        description=DESCRIPTION,
        openapi_tags=[
            {"name": "tickets", "description": "Classify support tickets."},
            {"name": "history", "description": "See recent classifications."},
            {"name": "health", "description": "Check that the service runs."},
        ],
        docs_url="/docs" if settings.show_docs else None,
        redoc_url="/redoc" if settings.show_docs else None,
        openapi_url="/openapi.json" if settings.show_docs else None,
    )
    app.state.settings = settings
    if settings.api_key is None:
        logger.warning(
            "API_KEY is not set: /v1/classify accepts requests without a key"
        )
    app.state.classifier = make_classifier(settings.classifier_mode)
    app.state.history = None
    if settings.database_url:
        app.state.history = History(settings.database_url)
        try:
            app.state.history.setup()
        except HistoryUnavailable:
            logger.warning("the database does not answer yet: history is not ready")
    else:
        logger.info("DATABASE_URL is not set: history is off")

    @app.middleware("http")
    async def request_id_and_limits(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        length = request.headers.get("content-length")
        if length and int(length) > MAX_BODY_BYTES:
            response = error_response(
                request,
                413,
                "body_too_large",
                f"The body is larger than {MAX_BODY_BYTES} bytes.",
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "%s %s %d %.0fms id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request.state.request_id,
        )
        return response

    if settings.allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type", "X-API-Key"],
        )

    add_error_handlers(app)
    app.include_router(router)

    @app.get("/health", tags=["health"], summary="Check that the service runs")
    def health() -> Health:
        return Health(status="ok")

    @app.get(
        "/ready",
        tags=["health"],
        summary="Check that the service can classify tickets",
        responses={503: {"model": ErrorResponse, "description": "Not ready."}},
    )
    def ready() -> Readiness:
        app.state.classifier.predict("readiness check")
        if app.state.history is not None:
            app.state.history.check()
        return Readiness(status="ready")

    return app


try:
    app = create_app()
except SettingsError as error:
    raise SystemExit(f"Settings error: {error}") from None
