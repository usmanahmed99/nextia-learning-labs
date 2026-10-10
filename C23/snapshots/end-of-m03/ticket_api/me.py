"""GET /v1/me: who is calling, and in which organizations (the authentication course, Module 2).

The identity (who) comes from the checked access token. The memberships (where, with which
role) come from the API's own tables: the token says nothing about them."""

from fastapi import APIRouter

from ticket_api import repository
from ticket_api.models import ErrorResponse, Me
from ticket_api.security import CurrentIdentity
from ticket_api.tickets import DB

router = APIRouter(prefix="/v1", tags=["me"])


@router.get(
    "/me",
    summary="Who am I?",
    responses={
        401: {"model": ErrorResponse, "description": "No access token, or it fails a check."},
        503: {"model": ErrorResponse, "description": "The provider or the database is down."},
    },
)
def me(identity: CurrentIdentity, db: DB) -> Me:
    with db.connection() as conn:
        user = repository.get_user(conn, identity.user_id)
        memberships = repository.memberships_of(conn, identity.user_id)
    return Me(
        user_id=identity.user_id,
        kind=identity.kind,
        name=user["name"] if user else None,
        platform_role=user["platform_role"] if user else None,
        client_id=identity.client_id,
        scopes=sorted(identity.scopes),
        token_expires_at=identity.expires_at,
        memberships=memberships,
    )
