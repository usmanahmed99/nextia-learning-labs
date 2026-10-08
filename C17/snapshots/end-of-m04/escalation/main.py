"""The escalation service: Larkfield's C05 model behind an HTTP API.

Start-up does the slow work once: read the settings, check and load the
bundle, score the parity cases. Only then does the service accept requests.
Each request does only the fast work: check the ticket, score it, answer.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from escalation.bundle import BundleError, load_bundle
from escalation.errors import add_error_handlers, error_response
from escalation.jobs import JobRunner
from escalation.routes import router
from escalation.settings import Settings, SettingsError, load_settings

MAX_BODY_BYTES = 2_000_000  # about 5,000 tickets for a job; one ticket is about 300 bytes

logger = logging.getLogger("escalation")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logging.basicConfig(level=settings.log_level, format="%(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        started = time.perf_counter()
        try:
            app.state.bundle = load_bundle(settings.model_bundle, settings.model_sha256)
        except BundleError as error:
            logger.error("Start-up error: %s", error)
            raise
        app.state.jobs = JobRunner(
            lambda: app.state.bundle, settings.max_queued_jobs, settings.extra_ms_per_ticket
        )
        logger.info(
            "model %s loaded (bundle %s...) in %.0f ms",
            app.state.bundle.version,
            app.state.bundle.digest[:12],
            (time.perf_counter() - started) * 1000,
        )
        yield

    app = FastAPI(
        title="Escalation Service",
        version="1.0.0",
        description="Scores new support tickets for the risk of escalation within 72 hours.",
        lifespan=lifespan,
        docs_url="/docs" if settings.show_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.show_docs else None,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_id_and_limits(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        length = request.headers.get("content-length")
        if length and int(length) > MAX_BODY_BYTES:
            response = error_response(
                request, 413, "body_too_large", f"The body is larger than {MAX_BODY_BYTES} bytes."
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        logger.info(
            "%s %s %d %.1fms id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request.state.request_id,
        )
        return response

    add_error_handlers(app)
    app.include_router(router)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    def ready(request: Request) -> dict:
        bundle = getattr(request.app.state, "bundle", None)
        if bundle is None:
            return error_response(request, 503, "not_ready", "The model is not loaded.")
        return {"status": "ready", "model_version": bundle.version}

    return app


try:
    app = create_app()
except (SettingsError, BundleError) as error:
    raise SystemExit(f"Start-up error: {error}") from None
