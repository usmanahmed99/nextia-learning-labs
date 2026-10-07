import asyncio
from typing import Annotated, get_args

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool

from ticket_api.classifier import ClassifierUnavailable, KeywordClassifier
from ticket_api.history import HistoryUnavailable
from ticket_api.models import (
    Category,
    CategoryList,
    Classification,
    ErrorResponse,
    HistoryList,
    TicketIn,
)
from ticket_api.security import require_api_key

logger = logging.getLogger("ticket_api")

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
    result = Classification(
        category=prediction.category,
        priority=prediction.priority,
        confidence=prediction.confidence,
        model_version=classifier.version,
    )
    history = request.app.state.history
    if history is not None:
        try:
            await run_in_threadpool(
                history.add, request.state.request_id, result.model_dump()
            )
        except HistoryUnavailable:
            logger.warning("history not saved id=%s", request.state.request_id)
    return result


@router.get(
    "/history",
    tags=["history"],
    summary="List recent classifications",
    description=(
        "Returns the newest classifications first. History is off when the "
        "server has no DATABASE_URL."
    ),
    responses={
        401: {
            "model": ErrorResponse,
            "description": "The API key is missing or wrong.",
        },
        503: {
            "model": ErrorResponse,
            "description": "History is off, or the database does not answer.",
        },
    },
    dependencies=[Depends(require_api_key)],
)
async def list_history(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100, description="How many to return.")] = 10,
) -> HistoryList:
    history = request.app.state.history
    if history is None:
        raise HistoryUnavailable("history is off: DATABASE_URL is not set")
    items = await run_in_threadpool(history.recent, limit)
    return HistoryList(items=items)
