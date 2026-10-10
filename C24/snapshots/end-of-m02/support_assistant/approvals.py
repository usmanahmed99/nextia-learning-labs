"""Approval before a write: the assistant proposes, a person decides.

A write the checks allow is not run. It waits in the `approvals` table of the database. A person
lists the waiting proposals (`approvals`) and approves or rejects one
(`approve ID --as USER`, `reject ID --as USER`).

The approver is checked in code, like the assistant was: the server reads the approver's role from
its membership table, a read-only member may not approve, and the approver's own refund limit
applies (a staff member may approve a refund of at most 100 dollars; the owner may approve more).
The checks of tools.check_write run again at decision time, so an order that changed since the
proposal is caught.
"""

import json
from contextlib import closing

from .designs import controls_for
from .identity import Session
from .systems import now

def queue(world, state, proposal, evidence: dict) -> str:
    """Put one allowed proposal in the approval queue. Returns its approval ID (AP-0001, ...)."""
    with closing(world._con()) as con:
        n = con.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
        approval_id = f"AP-{n + 1:04d}"
        con.execute("INSERT INTO approvals (approval_id,tenant,run_id,case_id,requested_by,tool,arguments,evidence,"
                    "status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (approval_id, state.tenant, state.run_id, state.case_id, state.user, proposal.tool,
                     json.dumps(proposal.arguments, ensure_ascii=False), json.dumps(evidence, ensure_ascii=False),
                     "pending", now()))
        con.commit()
    world.log(state.user, state.tenant, proposal.tool, "queued", approval=approval_id)
    return approval_id


def listing(world, status: str | None = None) -> list[dict]:
    with closing(world._con()) as con:
        q, args = "SELECT * FROM approvals", []
        if status:
            q, args = q + " WHERE status=?", [status]
        return [_row(r) for r in con.execute(q + " ORDER BY approval_id", args)]


def get(world, approval_id: str) -> dict | None:
    with closing(world._con()) as con:
        row = con.execute("SELECT * FROM approvals WHERE approval_id=?", (approval_id,)).fetchone()
        return _row(row) if row else None


def _row(row) -> dict:
    d = dict(row)
    d["arguments"] = json.loads(d["arguments"])
    d["evidence"] = json.loads(d["evidence"])
    return d


def decide(world, approval_id: str, approver: str, approve: bool, reason: str = "") -> str:
    """Approve (and run) or reject one waiting proposal. Returns a message for the person."""
    from .tools import check_write
    a = get(world, approval_id)
    if a is None:
        return f"No approval {approval_id}."
    if a["status"] != "pending":
        return f"{approval_id} is already {a['status']}."
    role = world.role_in(approver, a["tenant"])
    if role is None:
        return f"{approver} has no membership in {a['tenant']}: not allowed to decide."
    session = Session(sub=approver, tenant=a["tenant"], role=role)
    if not session.may_write():
        world.log(approver, a["tenant"], "approval", "refused", approval=approval_id, reason="read-only member")
        return "A read-only member may not approve or reject a change."
    if not approve:
        _close(world, approval_id, "rejected", approver, role, reason)
        world.log(approver, a["tenant"], a["tool"], "rejected", approval=approval_id)
        return f"{approval_id} rejected."
    ticket = world.ticket(a["evidence"]["ticket"], tenant=a["tenant"])
    refused = check_write(a["tool"], a["arguments"], controls_for(a["evidence"].get("design", "secure")),
                          session, ticket, world)
    if refused:
        world.log(approver, a["tenant"], "approval", "refused", approval=approval_id, reason=refused)
        return f"Not approved: {refused} It is still waiting."
    result = world.write(a["tool"], a["tenant"], a["arguments"], actor=approver, approval_id=approval_id)
    _close(world, approval_id, "approved", approver, role, reason)
    world.log(approver, a["tenant"], a["tool"], "executed", approval=approval_id, id=result["id"])
    return f"{approval_id} approved and done: {result['id']}."


def _close(world, approval_id, status, approver, role, reason) -> None:
    with closing(world._con()) as con:
        con.execute("UPDATE approvals SET status=?, decided_by=?, decided_role=?, reason=?, decided_at=? "
                    "WHERE approval_id=?", (status, approver, role, reason, now(), approval_id))
        con.commit()
