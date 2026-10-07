import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ticket_api.classifier import KeywordClassifier
from ticket_api.errors import add_error_handlers
from ticket_api.models import Health
from ticket_api.routes import router

DESCRIPTION = """
Classifies support tickets into a category and a priority.

The classifier is a deterministic mock: it uses keywords, so the same text
always gives the same result. Every error has the same shape:
`{"error": {"code": ..., "message": ..., "fields": [...]}}`.
"""

show_docs = os.environ.get("SHOW_DOCS", "true").lower() == "true"

app = FastAPI(
    title="Ticket Classifier API",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=[
        {"name": "tickets", "description": "Classify support tickets."},
        {"name": "health", "description": "Check that the service runs."},
    ],
    docs_url="/docs" if show_docs else None,
    redoc_url="/redoc" if show_docs else None,
    openapi_url="/openapi.json" if show_docs else None,
)
app.state.classifier = KeywordClassifier()
add_error_handlers(app)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
app.include_router(router)


@app.get("/health", tags=["health"], summary="Check that the service runs")
def health() -> Health:
    return Health(status="ok")
