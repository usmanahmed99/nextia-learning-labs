"""Privileged operations (the authentication course, Module 5).

A platform administrator (users.platform_role = 'platform_admin', read from the database, not
from the token) is NOT a member of any organization and reads no organization's tickets by
default. To help an organization, they ask for support access: a reason, at most 60 minutes,
read-only tickets. The organization's owner sees every grant and every use in the audit.

POST /v1/admin/tenants/{tenant}/support-access    platform administrator: a grant, with a reason
POST /v1/admin/support-access/{grant_id}/revoke   platform administrator: end it early
POST /v1/admin/tenants/{tenant}/delete            platform administrator: delete an organization
GET  /v1/tenants/{tenant}/support-access          owner: the grants for this organization
GET  /v1/tenants/{tenant}/audit                   owner: the organization's audit events
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ticket_api import audit, repository
from ticket_api.auth import Identity
from ticket_api.deps import DB
from ticket_api.models import (
    AuditList,
    ErrorResponse,
    Job,
    SupportGrant,
    SupportGrantIn,
    SupportGrantList,
    TenantDeletion,
)
from ticket_api.security import CurrentIdentity
from ticket_api.tenancy import Caller, TenantId, require

router = APIRouter(tags=["administration"])
ERRORS = {
    403: {"model": ErrorResponse, "description": "Platform administrators only."},
    404: {"model": ErrorResponse, "description": "No such organization or grant."},
}


class NotPlatformAdmin(Exception):
    """The caller is not a platform administrator."""


def platform_admin(identity: CurrentIdentity, db: DB, request: Request) -> Identity:
    with db.connection() as conn:
        user = repository.get_user(conn, identity.user_id)
    if identity.kind != "user" or user is None or user["platform_role"] != "platform_admin":
        audit.record(
            db,
            action=f"admin {request.method} {request.url.path}",
            result="denied",
            actor_id=identity.user_id,
            actor_kind=identity.kind,
            reason="not a platform administrator",
            request_id=request.state.request_id,
        )
        raise NotPlatformAdmin("Only a platform administrator may do this.")
    return identity


Admin = Annotated[Identity, Depends(platform_admin)]


def active_tenant(conn, tenant_id: str) -> None:
    row = conn.execute("SELECT status FROM tenants WHERE tenant_id = %s", (tenant_id,)).fetchone()
    if row is None or row["status"] != "active":
        raise repository.NotFound(f"Organization {tenant_id} does not exist.")


@router.post(
    "/v1/admin/tenants/{tenant}/support-access",
    status_code=201,
    summary="Get time-limited, read-only support access",
    responses=ERRORS,
)
def grant(
    tenant: TenantId, body: SupportGrantIn, admin: Admin, db: DB, request: Request
) -> SupportGrant:
    with db.connection() as conn:
        active_tenant(conn, tenant)
        row = conn.execute(
            "INSERT INTO support_grants (grant_id, tenant_id, user_id, reason, expires_at)"
            " VALUES (%s, %s, %s, %s, now() + make_interval(mins => %s)) RETURNING *",
            (str(uuid.uuid4()), tenant, admin.user_id, body.reason, body.minutes),
        ).fetchone()
        audit.write(
            conn,
            action="support_access.granted",
            result="done",
            actor_id=admin.user_id,
            tenant_id=tenant,
            target=admin.user_id,
            reason=body.reason,
            request_id=request.state.request_id,
            details={"grant_id": str(row["grant_id"]), "minutes": body.minutes},
        )
    return SupportGrant(**row)


@router.post(
    "/v1/admin/support-access/{grant_id}/revoke",
    summary="End support access early",
    responses=ERRORS,
)
def revoke_grant(grant_id: uuid.UUID, admin: Admin, db: DB, request: Request) -> SupportGrant:
    with db.connection() as conn:
        row = conn.execute(
            "UPDATE support_grants SET revoked_at = now() WHERE grant_id = %s"
            " AND revoked_at IS NULL RETURNING *",
            (str(grant_id),),
        ).fetchone()
        if row is None:
            raise repository.NotFound(f"Grant {grant_id} does not exist or ended.")
        audit.write(
            conn,
            action="support_access.revoked",
            result="done",
            actor_id=admin.user_id,
            tenant_id=row["tenant_id"],
            target=str(grant_id),
            request_id=request.state.request_id,
        )
    return SupportGrant(**row)


@router.post(
    "/v1/admin/tenants/{tenant}/delete",
    status_code=202,
    summary="Delete an organization (in the background)",
    responses=ERRORS,
)
def delete_tenant(
    tenant: TenantId, body: TenantDeletion, admin: Admin, db: DB, request: Request
) -> Job:
    with db.connection() as conn:
        active_tenant(conn, tenant)
        conn.execute("UPDATE tenants SET status = 'deleting' WHERE tenant_id = %s", (tenant,))
        job = repository.create_job(
            conn, str(uuid.uuid4()), admin.user_id, "tenant_delete", {}, tenant_id=tenant
        )
        audit.write(
            conn,
            action="tenant.deletion_requested",
            result="done",
            actor_id=admin.user_id,
            tenant_id=tenant,
            target=tenant,
            reason=body.reason,
            request_id=request.state.request_id,
            details={"job_id": str(job["job_id"])},
        )
    request.app.state.cache.drop_tenant(tenant)
    return Job(**job)


@router.get(
    "/v1/tenants/{tenant}/support-access",
    summary="Support access to this organization",
    responses=ERRORS,
)
def grants(caller: Annotated[Caller, Depends(require("audit.read"))], db: DB) -> SupportGrantList:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT * FROM support_grants WHERE tenant_id = %s ORDER BY created_at DESC",
            (caller.tenant_id,),
        ).fetchall()
    return SupportGrantList(items=rows)


@router.get(
    "/v1/tenants/{tenant}/audit", summary="The organization's audit events", responses=ERRORS
)
def audit_events(
    caller: Annotated[Caller, Depends(require("audit.read"))],
    db: DB,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    action: Annotated[str | None, Query(max_length=60)] = None,
) -> AuditList:
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_events WHERE tenant_id = %(t)s"
            " AND (%(a)s::text IS NULL OR action = %(a)s) ORDER BY event_id DESC LIMIT %(n)s",
            {"t": caller.tenant_id, "a": action, "n": limit},
        ).fetchall()
    return AuditList(items=rows)

