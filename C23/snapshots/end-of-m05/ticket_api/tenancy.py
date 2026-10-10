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

import threading
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Path, Request

from ticket_api import audit, repository
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


class MembershipCache:
    """Remembers roles for MEMBERSHIP_CACHE_SECONDS (default 0: off, every request asks the
    database). Faster, but a removed member keeps access until the entry expires (Module 5
    measures how long)."""

    def __init__(self, seconds: float = 0):
        self.seconds = seconds
        self._items: dict[tuple[str, str], tuple[float, str | None]] = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            found = self._items.get(key)
            return found[1] if found and found[0] > time.monotonic() else ...

    def set(self, key, role) -> None:
        if self.seconds > 0:
            with self._lock:
                self._items[key] = (time.monotonic() + self.seconds, role)


def role_of(
    request: Request, db: Database, identity: Identity, tenant_id: str
) -> tuple[str | None, dict | None]:
    """The caller's role in the organization: a membership, else an active support grant of a
    platform administrator (Module 5), else None. Returns (role, grant)."""
    cache = request.app.state.memberships
    key = (tenant_id, identity.user_id)
    role = cache.get(key)
    if role is not ...:
        return role, None
    grant = None
    with db.connection() as conn:
        role = repository.membership_role(conn, tenant_id, identity.user_id)
        if role is None and identity.kind == "user":
            grant = repository.active_support_grant(conn, tenant_id, identity.user_id)
            role = "support" if grant else None
    if grant is None:  # support access is never cached: every use is checked and recorded
        cache.set(key, role)
    return role, grant


def check(
    request: Request, db: Database, identity: Identity, tenant_id: str, action: str
) -> Caller:
    role, grant = role_of(request, db, identity, tenant_id)
    decision = decide(role, action, identity.scopes)
    if grant is not None:
        audit.record(
            db,
            action="support_access.used",
            result="allowed" if decision.allowed else "denied",
            actor_id=identity.user_id,
            tenant_id=tenant_id,
            target=f"{request.method} {request.url.path}",
            reason=grant["reason"],
            request_id=getattr(request.state, "request_id", None),
            details={"grant_id": str(grant["grant_id"]), "action": action},
        )
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
