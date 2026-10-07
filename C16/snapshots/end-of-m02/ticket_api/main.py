from fastapi import FastAPI

from ticket_api.classifier import KeywordClassifier
from ticket_api.routes import router

app = FastAPI(title="Ticket Classifier API")
app.state.classifier = KeywordClassifier()
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
