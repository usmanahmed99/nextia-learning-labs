"""The help desk's tickets: list, read, add a message, find similar tickets."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from ticket_api import repository
from ticket_api.db import Database, DatabaseUnavailable
from ticket_api.models import (
    ErrorResponse,
    Message,
    MessageIn,
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
def add_message(ticket_id: TicketId, message: MessageIn, db: DB) -> Message:
    with db.connection() as conn:
        row = repository.add_message(conn, ticket_id, message.author, message.body)
    return Message(**row)
