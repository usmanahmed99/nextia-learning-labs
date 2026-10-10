"""The organization of a request, and the check that runs before every protected route
(Module 4 of the authentication course).

    @router.get("/v1/tenants/{tenant}/tickets")
    def list_tickets(caller: Annotated[Caller, Depends(require("ticket.read"))], ...):
        repository.list_tickets(conn, tenant_id=caller.tenant_id, ...)

`require(action)` answers the three questions in order:
1. who:   the checked identity (token or session), else 401
2. where: the caller's membership in the organization of the PATH, else 404
3. what:  the membership's role and the token's scopes allow the action, else 403

The organization comes from the path and is checked against the caller's own membership.
A tenant ID in a header, a query parameter or a body is never used.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path, Request

from ticket_api import repository
from ticket_api.access import Decision, decide
from ticket_api.auth import Identity
from ticket_api.db import Database
from ticket_api.deps import get_db
from ticket_api.security import CurrentIdentity

TenantId = Annotated[str, Path(pattern=r"^[a-z][a-z0-9-]{1,30}$", examples=["larkfield"])]


class AccessDenied(Exception):
    """The caller may not do this here: 404 (not a member) or 403 (a role or scope too small)."""

    def __init__(self, decision: Decision, tenant_id: str, action: str):
        super().__init__(decision.rule)
        self.decision, self.tenant_id, self.action = decision, tenant_id, action


@dataclass(frozen=True)
class Caller:
    """A checked request: who, in which organization, with which role."""

    identity: Identity
    tenant_id: str
    role: str
    action: str

    @property
    def user_id(self) -> str:
        return self.identity.user_id

    def may(self, action: str) -> bool:
        return decide(self.role, action, self.identity.scopes).allowed


def check(
    request: Request, db: Database, identity: Identity, tenant_id: str, action: str
) -> Caller:
    with db.connection() as conn:
        role = repository.membership_role(conn, tenant_id, identity.user_id)
    decision = decide(role, action, identity.scopes)
    if not decision.allowed:
        raise AccessDenied(decision, tenant_id, action)
    caller = Caller(identity, tenant_id, role, action)
    request.state.caller = caller
    return caller


def require(action: str):
    """A FastAPI dependency: the route runs only if the caller may do `action` in the
    organization named in the path."""

    def dependency(
        request: Request,
        tenant: TenantId,
        identity: CurrentIdentity,
        db: Annotated[Database, Depends(get_db)],
    ) -> Caller:
        return check(request, db, identity, tenant, action)

    return dependency
