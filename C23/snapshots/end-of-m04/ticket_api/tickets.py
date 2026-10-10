"""One organization's tickets: list, read, add a message, find similar tickets.

Every route is under /v1/tenants/{tenant}/ and runs only after the access check
(ticket_api/tenancy.py): the caller is a member of that organization, and the role and
the token's scopes allow the action. Every query has the organization in it.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from ticket_api import repository
from ticket_api.cache import cache_key
from ticket_api.deps import DB, get_db
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
from ticket_api.tenancy import Caller, require

__all__ = ["DB", "get_db", "router", "TicketId"]

router = APIRouter(prefix="/v1/tenants/{tenant}/tickets", tags=["tickets"])

TicketId = Annotated[str, Path(pattern=r"^T-[0-9]{5,6}$", examples=["T-30002"])]
ERRORS = {
    401: {"model": ErrorResponse, "description": "No identity: sign in or send an access token."},
    403: {"model": ErrorResponse, "description": "A member, but the role or scope is too small."},
    404: {"model": ErrorResponse, "description": "No such organization, membership or ticket."},
    503: {"model": ErrorResponse, "description": "The database is not available or busy."},
}
Read = Annotated[Caller, Depends(require("ticket.read"))]
Write = Annotated[Caller, Depends(require("ticket.write"))]


@router.get("", summary="List tickets", responses=ERRORS)
def list_tickets(
    caller: Read,
    db: DB,
    status: Status | None = None,
    team: Team | None = None,
    customer_id: Annotated[str | None, Query(pattern=r"^[A-Z]-[0-9]{4,5}$")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="How many tickets per page.")] = 20,
    after: Annotated[
        str | None, Query(description="The `next` value of the previous page.")
    ] = None,
) -> TicketPage:
    with db.connection(caller.tenant_id) as conn:
        page = repository.list_tickets(
            conn,
            tenant_id=caller.tenant_id,
            status=status,
            team=team,
            customer_id=customer_id,
            limit=limit,
            after=after,
        )
    return TicketPage(**page)


@router.get("/{ticket_id}", summary="Read one ticket with its messages and files", responses=ERRORS)
def get_ticket(ticket_id: TicketId, caller: Read, db: DB) -> TicketDetail:
    with db.connection(caller.tenant_id) as conn:
        ticket = repository.get_ticket(conn, ticket_id, tenant_id=caller.tenant_id)
    return TicketDetail(**ticket)


@router.post(
    "/{ticket_id}/messages", status_code=201, summary="Add a message to a ticket", responses=ERRORS
)
def add_message(ticket_id: TicketId, message: MessageIn, caller: Write, db: DB) -> Message:
    with db.connection(caller.tenant_id) as conn:
        row = repository.add_message(
            conn, ticket_id, message.author, message.body, tenant_id=caller.tenant_id
        )
    return Message(**row)


@router.get(
    "/{ticket_id}/similar",
    summary="Find similar tickets",
    description="The tickets of the same organization whose text is closest in meaning.",
    responses=ERRORS,
)
def similar(
    ticket_id: TicketId,
    caller: Read,
    db: DB,
    request: Request,
    k: Annotated[int, Query(ge=1, le=20)] = 5,
    team: Team | None = None,
    status: Status | None = None,
) -> SimilarList:
    cache = request.app.state.cache
    with db.connection(caller.tenant_id) as conn:
        version = repository.current_embedding_version(conn)
        if version is None:
            raise repository.NotFound("No embedding version is current.")
        # The key starts with the organization: the same ticket ID and filters in another
        # organization can never find this entry. (The access check has already run.)
        key = cache_key(caller.tenant_id, "similar", ticket_id, k, team, status, version)
        result = cache.get(key)
        if result is None:
            items = repository.similar_tickets(
                conn,
                ticket_id,
                tenant_id=caller.tenant_id,
                k=k,
                version=version,
                team=team,
                status=status,
            )
            result = SimilarList(embedding_version=version, items=items)
            cache.set(key, result)
    return result
