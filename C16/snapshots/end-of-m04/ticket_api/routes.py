from typing import Annotated, get_args

from fastapi import APIRouter, Depends, Request

from ticket_api.classifier import KeywordClassifier
from ticket_api.models import (
    Category,
    CategoryList,
    Classification,
    ErrorResponse,
    TicketIn,
)

router = APIRouter(prefix="/v1", tags=["tickets"])


def get_classifier(request: Request) -> KeywordClassifier:
    return request.app.state.classifier


@router.get("/categories", summary="List the ticket categories")
def list_categories() -> CategoryList:
    return CategoryList(categories=list(get_args(Category)))


@router.post(
    "/classify",
    summary="Classify a support ticket",
    description=(
        "Predicts the category and priority of one ticket from its subject and body. "
        "The same text always gives the same result."
    ),
    response_description="The predicted category and priority",
    responses={
        422: {
            "model": ErrorResponse,
            "description": "A field is missing or not valid.",
        },
    },
)
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
