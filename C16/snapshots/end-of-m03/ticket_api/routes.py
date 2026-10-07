from typing import Annotated, get_args

from fastapi import APIRouter, Depends, Request

from ticket_api.classifier import KeywordClassifier
from ticket_api.models import Category, CategoryList, Classification, TicketIn

router = APIRouter(prefix="/v1", tags=["tickets"])


def get_classifier(request: Request) -> KeywordClassifier:
    return request.app.state.classifier


@router.get("/categories")
def list_categories() -> CategoryList:
    return CategoryList(categories=list(get_args(Category)))


@router.post("/classify")
def classify(
    ticket: TicketIn,
    classifier: Annotated[KeywordClassifier, Depends(get_classifier)],
) -> Classification:
    prediction = classifier.predict(f"{ticket.subject}\n{ticket.body}")
    return Classification(
        category=prediction.category,
        priority=prediction.priority,
        confidence=prediction.confidence,
        model_version=classifier.version,
    )
