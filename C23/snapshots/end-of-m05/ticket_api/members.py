"""Members and invitations of an organization (the authentication course, Module 5).

GET    /v1/tenants/{tenant}/members                  owner, staff
PATCH  /v1/tenants/{tenant}/members/{user_id}        owner: change a role
DELETE /v1/tenants/{tenant}/members/{user_id}        owner: remove a member
POST   /v1/tenants/{tenant}/invitations              owner: invite an email address, with a role
DELETE /v1/tenants/{tenant}/invitations/{id}         owner: take an invitation back
POST   /v1/invitations/accept                        the invited person, signed in

A change takes effect at the caller's NEXT request: every request reads the membership again
(MEMBERSHIP_CACHE_SECONDS=0). Every change writes an audit event in the same transaction.
"""

import hashlib
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from ticket_api import audit, repository
from ticket_api.deps import DB
from ticket_api.models import (
    ErrorResponse,
    Invitation,
    InvitationAccept,
    InvitationIn,
    MemberList,
    MembershipInfo,
    RoleChange,
)
from ticket_api.security import CurrentIdentity
from ticket_api.tenancy import Caller, require

router = APIRouter(tags=["members"])
UserId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_.:@|-]{1,100}$")]
Manage = Annotated[Caller, Depends(require("member.manage"))]
ERRORS = {
    403: {"model": ErrorResponse, "description": "Only an owner may do this."},
    404: {"model": ErrorResponse, "description": "No such organization, membership or member."},
    409: {"model": ErrorResponse, "description": "The organization needs at least one owner."},
}


def event(request: Request, caller: Caller, action: str, target: str, **details) -> dict:
    return {
        "action": action,
        "result": "done",
        "actor_id": caller.user_id,
        "tenant_id": caller.tenant_id,
        "target": target,
        "request_id": request.state.request_id,
        "details": details,
    }


@router.get("/v1/tenants/{tenant}/members", summary="List the members", responses=ERRORS)
def members(caller: Annotated[Caller, Depends(require("member.read"))], db: DB) -> MemberList:
    with db.connection(caller.tenant_id) as conn:
        return MemberList(items=repository.list_members(conn, tenant_id=caller.tenant_id))


@router.patch(
    "/v1/tenants/{tenant}/members/{user_id}", summary="Change a member's role", responses=ERRORS
)
def change_role(
    user_id: UserId, change: RoleChange, caller: Manage, db: DB, request: Request
) -> MembershipInfo:
    with db.connection(caller.tenant_id) as conn:
        roles = repository.change_role(conn, user_id, change.role, tenant_id=caller.tenant_id)
        audit.write(conn, **event(request, caller, "member.role_changed", user_id, **roles))
        name = conn.execute(
            "SELECT name FROM tenants WHERE tenant_id = %s", (caller.tenant_id,)
        ).fetchone()["name"]
    request.app.state.cache.drop_tenant(caller.tenant_id)
    return MembershipInfo(tenant_id=caller.tenant_id, tenant_name=name, role=change.role)


@router.delete(
    "/v1/tenants/{tenant}/members/{user_id}",
    status_code=204,
    summary="Remove a member",
    responses=ERRORS,
)
def remove(user_id: UserId, caller: Manage, db: DB, request: Request) -> Response:
    with db.connection(caller.tenant_id) as conn:
        role = repository.remove_member(conn, user_id, tenant_id=caller.tenant_id)
        audit.write(conn, **event(request, caller, "member.removed", user_id, role=role))
    request.app.state.cache.drop_tenant(caller.tenant_id)
    return Response(status_code=204)


@router.post(
    "/v1/tenants/{tenant}/invitations",
    status_code=201,
    summary="Invite a person by email address",
    responses=ERRORS,
)
def invite(invitation: InvitationIn, caller: Manage, db: DB, request: Request) -> Invitation:
    code = secrets.token_urlsafe(24)  # shown once; only its SHA-256 is kept
    with db.connection(caller.tenant_id) as conn:
        row = repository.create_invitation(
            conn,
            str(uuid.uuid4()),
            invitation.email,
            invitation.role,
            hashlib.sha256(code.encode()).hexdigest(),
            caller.user_id,
            invitation.expires_in_hours,
            tenant_id=caller.tenant_id,
        )
        audit.write(
            conn,
            **event(request, caller, "invitation.created", row["email"], role=invitation.role),
        )
    return Invitation(**row, code=code)


@router.delete(
    "/v1/tenants/{tenant}/invitations/{invitation_id}",
    status_code=204,
    summary="Take an invitation back",
    responses=ERRORS,
)
def revoke(invitation_id: uuid.UUID, caller: Manage, db: DB, request: Request) -> Response:
    with db.connection(caller.tenant_id) as conn:
        done = conn.execute(
            "UPDATE invitations SET revoked_at = now() WHERE tenant_id = %s AND invitation_id = %s"
            " AND accepted_at IS NULL AND revoked_at IS NULL",
            (caller.tenant_id, str(invitation_id)),
        ).rowcount
        if not done:
            raise repository.NotFound("This invitation does not exist or was used.")
        audit.write(conn, **event(request, caller, "invitation.revoked", str(invitation_id)))
    return Response(status_code=204)


@router.post(
    "/v1/invitations/accept",
    summary="Accept an invitation",
    responses={
        404: {"model": ErrorResponse, "description": "No such invitation for you."},
        409: {"model": ErrorResponse, "description": "Used already, or expired."},
    },
)
def accept(
    body: InvitationAccept, identity: CurrentIdentity, db: DB, request: Request
) -> MembershipInfo:
    digest = hashlib.sha256(body.code.encode()).hexdigest()
    with db.connection() as conn:
        user = repository.get_user(conn, identity.user_id)
        if user is None:
            raise repository.NotFound("This invitation does not exist.")
        try:
            joined = repository.accept_invitation(conn, digest, user)
        except repository.Conflict as conflict:
            failure = conflict
        else:
            failure = None
            audit.write(
                conn,
                action="invitation.accepted",
                result="done",
                actor_id=identity.user_id,
                tenant_id=joined["tenant_id"],
                target=identity.user_id,
                request_id=request.state.request_id,
                details={"role": joined["role"]},
            )
            name = conn.execute(
                "SELECT name FROM tenants WHERE tenant_id = %s", (joined["tenant_id"],)
            ).fetchone()["name"]
    if failure is not None:
        audit.record(
            db,
            action="invitation.accepted",
            result="denied",
            actor_id=identity.user_id,
            reason=failure.code,
            request_id=request.state.request_id,
        )
        raise failure
    return MembershipInfo(tenant_id=joined["tenant_id"], tenant_name=name, role=joined["role"])
