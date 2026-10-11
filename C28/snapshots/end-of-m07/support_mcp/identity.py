"""Who is the caller, what may they do, and in which organization?

The answer never comes from the model and never from the token alone:
- the user comes from the environment of a local (stdio) server, or from a validated access token;
- the organization comes from the connection (SUPPORT_TENANT, or the X-Support-Tenant header);
- the role comes from this server's own membership table (data/memberships.csv).
A user without a membership in the organization gets the same refusal for a real organization
and for a made-up one. Every refusal is a Refused error: the client sees only code -32003 and the
message; the server logs the reason, the user and the organization (server.py, http.py).
"""

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path

from mcp import MCPError

DATA = Path(__file__).resolve().parent.parent / "data"
FORBIDDEN = -32003  # an application error code (JSON-RPC leaves -32000 to -32099 to servers)
TENANT_HEADER = "x-support-tenant"

SCOPES = ("knowledge:read", "tickets:read", "refunds:propose")
LOCAL_SCOPES = "knowledge:read tickets:read"  # a local server gets read scopes unless told otherwise


@dataclass(frozen=True)
class Caller:
    user_id: str
    tenant: str
    role: str
    scopes: frozenset = field(default_factory=frozenset)
    client_id: str = "local"

    @property
    def staff(self) -> bool:
        return self.role in ("owner", "staff")


def load_memberships(data_dir: Path = DATA) -> dict[tuple[str, str], str]:
    with (data_dir / "memberships.csv").open(encoding="utf-8", newline="") as f:
        return {(r["user_id"], r["tenant_id"]): r["role"] for r in csv.DictReader(f)}


MEMBERSHIPS = load_memberships()


class Refused(MCPError):
    """A refusal (-32003) that also knows why and for whom, so that the server can log it."""

    def __init__(
        self, message: str, reason: str, user_id: str = "", tenant: str = "", role: str = "", client_id: str = ""
    ):
        super().__init__(code=FORBIDDEN, message=message)
        self.reason, self.user_id, self.tenant, self.role, self.client_id = reason, user_id, tenant, role, client_id

    def log_fields(self) -> dict:
        """What the log line says: who was refused, where, and why (never a token)."""
        fields = {"user": self.user_id, "tenant": self.tenant, "role": self.role, "client": self.client_id}
        return {k: v for k, v in fields.items() if v} | {"reason": self.reason}


def forbidden(message: str, reason: str = "forbidden", caller: "Caller | None" = None) -> Refused:
    if caller is None:
        return Refused(message, reason)
    return Refused(message, reason, caller.user_id, caller.tenant, caller.role, caller.client_id)


def resolve(user_id: str, tenant: str, scopes, client_id: str = "local") -> Caller:
    role = MEMBERSHIPS.get((user_id, tenant))
    if role is None:  # no membership, or no such organization: the same answer
        raise Refused(
            "forbidden: you have no access to this organization", "no_membership", user_id, tenant, client_id=client_id
        )
    return Caller(user_id, tenant, role, frozenset(scopes), client_id)


def require_scope(caller: Caller, scope: str) -> None:
    if scope not in caller.scopes:
        raise forbidden(f"insufficient_scope: this needs the scope {scope}", "insufficient_scope", caller)


def local_caller() -> Caller:
    """The caller of a local (stdio) server: the person who started it, from the environment."""
    user = os.environ.get("SUPPORT_USER", "usr-sam")
    tenant = os.environ.get("SUPPORT_TENANT", "larkfield")
    scopes = os.environ.get("SUPPORT_SCOPES", LOCAL_SCOPES).split()
    return resolve(user, tenant, scopes)


def http_caller(ctx) -> Caller:
    """The caller of a remote (Streamable HTTP) request: the validated token's user and scopes,
    the organization named by the connection's header, the role from the membership table."""
    from mcp.server.auth.middleware.auth_context import get_access_token

    token = get_access_token()
    if token is None or not token.subject:  # the HTTP app refuses this before; checked again here
        raise forbidden("forbidden: no signed-in user", "no_signed_in_user")
    tenant = (ctx.headers or {}).get(TENANT_HEADER, "")
    return resolve(token.subject, tenant, token.scopes, token.client_id)
