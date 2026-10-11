"""The one write: propose a refund. A mock: no money moves, ever.

Two separate gates protect it, and neither trusts the model:
1. Authorization, on the server, for the call itself: the scope refunds:propose, the role staff
   or owner in this organization (from the membership table), a ticket of this organization,
   and an amount within the agent's limit (the refund approval procedure: up to 100 dollars).
2. Approval, by a person, outside the AI application: the tool only records a *proposal* with
   the exact operation. An owner of the organization who is not the proposer approves it with
   `python -m support_mcp.approvals approve OP-0001 --user usr-grace`. Only then is it recorded.

The tool annotations say "not read-only". That is a hint for the application's user interface,
not a control: the checks above are the controls.
"""

import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from support_mcp import identity
from support_mcp.knowledge import NotFound

ROOT = Path(__file__).resolve().parent.parent
REFUND_LIMIT = Decimal("100.00")  # an agent's limit in Larkfield's refund approval procedure
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

Amount = Annotated[
    Decimal, Field(gt=0, le=10000, decimal_places=2, description="Amount in dollars, for example 25.00.")
]
Reason = Annotated[str, Field(min_length=3, max_length=200, description="Why the customer should get the refund.")]


class Proposal(BaseModel):
    operation_id: str
    status: str
    operation: dict
    proposed_by: str
    approver_role: str = "owner"
    message: str


def state_path() -> Path:
    return Path(os.environ.get("SUPPORT_STATE", ROOT / ".support" / "state.db"))


def connect() -> sqlite3.Connection:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(
        """CREATE TABLE IF NOT EXISTS proposals (
               n INTEGER PRIMARY KEY AUTOINCREMENT, tenant TEXT NOT NULL, ticket_id TEXT NOT NULL,
               amount TEXT NOT NULL, reason TEXT NOT NULL, proposed_by TEXT NOT NULL,
               status TEXT NOT NULL DEFAULT 'pending_approval', created_at TEXT NOT NULL,
               decided_by TEXT, decided_at TEXT);
           CREATE TABLE IF NOT EXISTS refunds (
               operation_id TEXT PRIMARY KEY, tenant TEXT, ticket_id TEXT, amount TEXT, recorded_at TEXT);"""
    )
    return db


def op_id(n: int) -> str:
    return f"OP-{n:04d}"


def as_proposal(r: sqlite3.Row, message: str) -> Proposal:
    return Proposal(
        operation_id=op_id(r["n"]),
        status=r["status"],
        proposed_by=r["proposed_by"],
        message=message,
        operation={
            "action": "refund",
            "organization": r["tenant"],
            "ticket_id": r["ticket_id"],
            "amount": r["amount"],
            "currency": "USD",
            "reason": r["reason"],
        },
    )


def register(mcp, knowledge, caller, log) -> None:
    @mcp.tool(annotations=WRITE)
    def propose_refund(
        ticket_id: Annotated[str, Field(pattern=r"^T-\d{5}$")], amount: Amount, reason: Reason, ctx: Context
    ) -> Proposal:
        """Propose a refund for a ticket of this organization. Nothing is refunded now: the tool records a proposal with the exact operation, and an owner of the organization must approve it outside this application. Amounts over 100.00 dollars are refused (they need a team lead)."""
        fields = {"tool": "propose_refund", "ticket_id": ticket_id, "amount": str(amount)}
        who = caller(ctx, "refunds:propose", **fields)  # membership and scope; a refusal is logged there
        if not who.staff:
            e = identity.forbidden(f"forbidden: the role {who.role} cannot propose a refund", "role", who)
            log.event("refused", **fields, **e.log_fields())
            raise e
        try:
            knowledge.ticket(who.tenant, ticket_id)
        except NotFound:
            log.event("tool_call", caller=who, outcome="not_found", **fields)
            raise ToolError(f"not_found: there is no ticket {ticket_id} in this organization") from None
        if amount > REFUND_LIMIT:
            log.event("tool_call", caller=who, outcome="over_limit", **fields)
            raise ToolError(
                f"over_limit: a refund over {REFUND_LIMIT} dollars needs a team lead; it cannot be proposed here"
            )
        amount_text = f"{amount:.2f}"
        with closing(connect()) as db, db:
            same = db.execute(
                """SELECT * FROM proposals WHERE tenant=? AND ticket_id=? AND amount=? AND proposed_by=?
                   AND status='pending_approval'""",
                (who.tenant, ticket_id, amount_text, who.user_id),
            ).fetchone()
            if same is not None:  # the same proposal again (a retry): no second proposal
                log.event("tool_call", caller=who, outcome="already_proposed", operation_id=op_id(same["n"]), **fields)
                return as_proposal(same, "This refund was already proposed. It waits for an owner's approval.")
            cur = db.execute(
                "INSERT INTO proposals (tenant, ticket_id, amount, reason, proposed_by, created_at) VALUES (?,?,?,?,?,?)",
                (
                    who.tenant,
                    ticket_id,
                    amount_text,
                    reason,
                    who.user_id,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                ),
            )
            row = db.execute("SELECT * FROM proposals WHERE n=?", (cur.lastrowid,)).fetchone()
        log.event("tool_call", caller=who, outcome="proposed", operation_id=op_id(row["n"]), **fields)
        return as_proposal(row, "Proposed, not done. An owner of the organization must approve it.")


class ApprovalError(Exception):
    pass


def decide(operation_id: str, user_id: str, approve: bool) -> dict:
    """An owner approves or rejects a proposal. The proposer cannot approve their own proposal."""
    n = int(operation_id.removeprefix("OP-")) if operation_id.startswith("OP-") else -1
    with closing(connect()) as db, db:
        r = db.execute("SELECT * FROM proposals WHERE n=?", (n,)).fetchone()
        if r is None:
            raise ApprovalError(f"{operation_id}: no such proposal")
        role = identity.MEMBERSHIPS.get((user_id, r["tenant"]))
        if role != "owner":
            raise ApprovalError(
                f"{operation_id}: only an owner of {r['tenant']} can decide (you: {role or 'no membership'})"
            )
        if user_id == r["proposed_by"]:
            raise ApprovalError(f"{operation_id}: you proposed it; another person must approve it")
        if r["status"] != "pending_approval":
            raise ApprovalError(f"{operation_id}: already {r['status']}")
        now = datetime.now(UTC).isoformat(timespec="seconds")
        status = "approved" if approve else "rejected"
        db.execute("UPDATE proposals SET status=?, decided_by=?, decided_at=? WHERE n=?", (status, user_id, now, n))
        if approve:
            db.execute(
                "INSERT INTO refunds VALUES (?,?,?,?,?)", (operation_id, r["tenant"], r["ticket_id"], r["amount"], now)
            )
        return {
            "operation_id": operation_id,
            "status": status,
            "ticket_id": r["ticket_id"],
            "amount": r["amount"],
            "tenant": r["tenant"],
            "decided_by": user_id,
        }


def pending(tenant: str | None = None) -> list[dict]:
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM proposals WHERE status='pending_approval' ORDER BY n").fetchall()
    return [as_proposal(r, "").model_dump(exclude={"message"}) for r in rows if tenant in (None, r["tenant"])]


def refunds() -> list[dict]:
    with closing(connect()) as db:
        return [dict(r) for r in db.execute("SELECT * FROM refunds ORDER BY operation_id")]
