import asyncio
from typing import Annotated, get_args

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool

from ticket_api.classifier import ClassifierUnavailable, KeywordClassifier
from ticket_api.models import (
    Category,
    CategoryList,
    Classification,
    ErrorResponse,
    TicketIn,
)
from ticket_api.security import require_api_key

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
        401: {
            "model": ErrorResponse,
            "description": "The API key is missing or wrong.",
        },
        413: {"model": ErrorResponse, "description": "The request body is too large."},
        422: {
            "model": ErrorResponse,
            "description": "A field is missing or not valid.",
        },
        503: {
            "model": ErrorResponse,
            "description": "The classifier is not available.",
        },
    },
    dependencies=[Depends(require_api_key)],
)
async def classify(
    ticket: TicketIn,
    request: Request,
    classifier: Annotated[KeywordClassifier, Depends(get_classifier)],
) -> Classification:
    text = f"{ticket.subject}\n{ticket.body}"
    timeout = request.app.state.settings.classifier_timeout
    try:
        prediction = await asyncio.wait_for(
            run_in_threadpool(classifier.predict, text), timeout
        )
    except TimeoutError:
        raise ClassifierUnavailable(f"no answer within {timeout} seconds") from None
    return Classification(
        category=prediction.category,
        priority=prediction.priority,
        confidence=prediction.confidence,
        model_version=classifier.version,
    )
