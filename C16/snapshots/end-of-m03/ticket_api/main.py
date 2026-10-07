import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ticket_api.classifier import KeywordClassifier
from ticket_api.errors import add_error_handlers
from ticket_api.routes import router

app = FastAPI(title="Ticket Classifier API")
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
