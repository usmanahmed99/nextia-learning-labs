import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ticket_api import tickets
from ticket_api.classifier import make_classifier
from ticket_api.config import Settings, SettingsError, load_settings
from ticket_api.db import QUERIES, Database
from ticket_api.errors import add_error_handlers, error_response
from ticket_api.history import History
from ticket_api.models import ErrorResponse, Health, Readiness
from ticket_api.routes import router

MAX_BODY_BYTES = 16_384

logger = logging.getLogger("ticket_api")

DESCRIPTION = """
Classifies support tickets into a category and a priority, and keeps the help
desk's tickets and messages.

The classifier is a deterministic mock: it uses keywords, so the same text
always gives the same result. Every error has the same shape:
`{"error": {"code": ..., "message": ..., "request_id": ..., "fields": [...]}}`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start-up: open the connection pool. Shutdown: close it, so that no
    # connection stays open on the database server.
    if app.state.db is not None:
        app.state.db.open()
    yield
    if app.state.db is not None:
        app.state.db.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s: %(message)s"
    )

    app = FastAPI(
        title="Ticket Classifier API",
        version="1.3.0",
        description=DESCRIPTION,
        openapi_tags=[
            {"name": "tickets", "description": "Classify, list and read support tickets."},
            {"name": "history", "description": "See recent classifications."},
            {"name": "health", "description": "Check that the service runs."},
        ],
        docs_url="/docs" if settings.show_docs else None,
        redoc_url="/redoc" if settings.show_docs else None,
        openapi_url="/openapi.json" if settings.show_docs else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    if settings.api_key is None:
        logger.warning(
            "API_KEY is not set: /v1/classify accepts requests without a key"
        )
    app.state.classifier = make_classifier(
        settings.classifier_mode, settings.classifier_version
    )
    app.state.db = None
    app.state.history = None
    if settings.database_url:
        app.state.db = Database(
            settings.database_url,
            pool=settings.db_pool,
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            timeout=settings.db_pool_timeout,
        )
        app.state.history = History(app.state.db)
    else:
        logger.info("DATABASE_URL is not set: history and tickets are off")

    @app.middleware("http")
    async def request_id_and_limits(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        queries = [0]
        token = QUERIES.set(queries)
        length = request.headers.get("content-length")
        try:
            if length and int(length) > MAX_BODY_BYTES:
                response = error_response(
                    request,
                    413,
                    "body_too_large",
                    f"The body is larger than {MAX_BODY_BYTES} bytes.",
                )
            else:
                response = await call_next(request)
        finally:
            QUERIES.reset(token)
        response.headers["X-Request-ID"] = request.state.request_id
        if settings.show_query_count:
            response.headers["X-DB-Queries"] = str(queries[0])
        logger.info(
            "%s %s %d %.0fms queries=%d id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            queries[0],
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
    app.include_router(tickets.router)

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
