"""The help desk's tickets: list, read, add a message, find similar tickets."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.concurrency import run_in_threadpool

from ticket_api import repository
from ticket_api.db import Database, DatabaseUnavailable
from ticket_api.models import (
    ErrorResponse,
    Message,
    MessageIn,
    SimilarList,
    Status,
    Team,
    TicketDetail,
    TicketPage,
)
from ticket_api.security import require_api_key

router = APIRouter(prefix="/v1/tickets", tags=["tickets"], dependencies=[Depends(require_api_key)])

TicketId = Annotated[str, Path(pattern=r"^T-[0-9]{5,6}$", examples=["T-30002"])]
ERRORS = {
    401: {"model": ErrorResponse, "description": "The API key is missing or wrong."},
    503: {"model": ErrorResponse, "description": "The database is not available or busy."},
}


def get_db(request: Request) -> Database:
    db = request.app.state.db
    if db is None:
        raise DatabaseUnavailable("DATABASE_URL is not set")
    return db


DB = Annotated[Database, Depends(get_db)]


@router.get("", summary="List tickets", responses=ERRORS)
def list_tickets(
    db: DB,
    status: Status | None = None,
    team: Team | None = None,
    customer_id: Annotated[str | None, Query(pattern=r"^C-[0-9]{4,5}$")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="How many tickets per page.")] = 20,
    after: Annotated[
        str | None, Query(description="The `next` value of the previous page.")
    ] = None,
) -> TicketPage:
    with db.connection() as conn:
        page = repository.list_tickets(
            conn, status=status, team=team, customer_id=customer_id, limit=limit, after=after
        )
    return TicketPage(**page)


@router.get(
    "/{ticket_id}",
    summary="Read one ticket with its messages and files",
    responses={404: {"model": ErrorResponse, "description": "No such ticket."}, **ERRORS},
)
def get_ticket(ticket_id: TicketId, db: DB) -> TicketDetail:
    with db.connection() as conn:
        ticket = repository.get_ticket(conn, ticket_id)
    return TicketDetail(**ticket)


@router.post(
    "/{ticket_id}/messages",
    status_code=201,
    summary="Add a message to a ticket",
    responses={404: {"model": ErrorResponse, "description": "No such ticket."}, **ERRORS},
)
async def add_message(
    ticket_id: TicketId, message: MessageIn, db: DB, request: Request
) -> Message:
    def save() -> tuple[dict, str | None]:
        with db.connection() as conn:
            row = repository.add_message(conn, ticket_id, message.author, message.body)
            return row, repository.ticket_customer(conn, ticket_id)

    row, customer_id = await run_in_threadpool(save)
    cache = request.app.state.cache
    if cache is not None and customer_id:
        # The ticket's status may have changed: the customer's cached answers are old now.
        await cache.invalidate(f"customer:{customer_id}")
    return Message(**row)


@router.get(
    "/{ticket_id}/similar",
    summary="Find similar tickets",
    description="The tickets whose text is closest in meaning, by their vectors (pgvector).",
    responses={
        404: {"model": ErrorResponse, "description": "No such ticket, or no vector."},
        **ERRORS,
    },
)
def similar(
    ticket_id: TicketId,
    db: DB,
    k: Annotated[int, Query(ge=1, le=20)] = 5,
    team: Team | None = None,
    status: Status | None = None,
) -> SimilarList:
    with db.connection() as conn:
        version = repository.current_embedding_version(conn)
        if version is None:
            raise repository.NotFound("No embedding version is current.")
        items = repository.similar_tickets(
            conn, ticket_id, k=k, version=version, team=team, status=status
        )
    return SimilarList(embedding_version=version, items=items)
