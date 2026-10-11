"""Who is the caller, what may they do, and in which organization?

The answer never comes from the model and never from the token alone:
- the user comes from the environment of the local (stdio) server: the person who started it;
- the organization comes from the connection (SUPPORT_TENANT), never from a tool argument;
- the role comes from this server's own membership table (data/memberships.csv).
A user without a membership in the organization gets the same refusal for a real organization
and for a made-up one.
"""

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path

from mcp import MCPError

DATA = Path(__file__).resolve().parent.parent / "data"
FORBIDDEN = -32003  # an application error code (JSON-RPC leaves -32000 to -32099 to servers)

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


def forbidden(message: str) -> MCPError:
    return MCPError(code=FORBIDDEN, message=message)


def resolve(user_id: str, tenant: str, scopes, client_id: str = "local") -> Caller:
    role = MEMBERSHIPS.get((user_id, tenant))
    if role is None:  # no membership, or no such organization: the same answer
        raise forbidden("forbidden: you have no access to this organization")
    return Caller(user_id, tenant, role, frozenset(scopes), client_id)


def require_scope(caller: Caller, scope: str) -> None:
    if scope not in caller.scopes:
        raise forbidden(f"insufficient_scope: this needs the scope {scope}")


def local_caller() -> Caller:
    """The caller of a local (stdio) server: the person who started it, from the environment."""
    user = os.environ.get("SUPPORT_USER", "usr-sam")
    tenant = os.environ.get("SUPPORT_TENANT", "larkfield")
    scopes = os.environ.get("SUPPORT_SCOPES", LOCAL_SCOPES).split()
    return resolve(user, tenant, scopes)
