"""Approval before a write: the assistant proposes, a person decides.

A write the checks allow is not run. It waits in the `approvals` table of the database. A person
lists the waiting proposals (`approvals`), reads one with its evidence (`review ID`), and approves or
rejects it with a reason (`approve ID --as USER --reason ...`, `reject ...`).

The approver is checked in code, like the assistant was: the server reads the approver's role from
its membership table, a read-only member may not approve, and the approver's own refund limit
applies (a staff member may approve a refund of at most 100 dollars; the owner may approve more).
The checks of tools.check_write run again at decision time, so an order that changed since the
proposal is caught.

A rejection is a disagreement with the assistant. It is written to the audit log with its reason,
so that the team can see where the assistant and people disagree and improve the assistant.
"""

import json
from contextlib import closing

from .designs import controls_for
from .identity import Session
from .systems import now


def evidence_for(state, case, ticket: dict) -> dict:
    """What a reviewer needs to decide: the request, the ticket, what the assistant read, and its draft."""
    reads = [e.summary for e in state.tool_events if e.ok and e.summary and "proposed" not in e.summary]
    blocked = [f"{e.tool}: {e.blocked_reason or e.code}" for e in state.tool_events if not e.ok and e.code != "ok"]
    return {"ticket": ticket["ticket_id"], "design": state.design, "request": case.request,
            "ticket_text": ticket["text"][:600], "reads": reads, "blocked": blocked,
            "draft": state.answer[:600]}


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


def review_text(world, approval_id: str) -> str:
    """The review screen: the proposed action, its evidence, the checks, and what to decide."""
    a = get(world, approval_id)
    if a is None:
        return f"No approval {approval_id}."
    ev = a["evidence"]
    args = a["arguments"]
    lines = [f"{a['approval_id']}  {a['status']}  tenant {a['tenant']}  ticket {ev.get('ticket')}  "
             f"(case {a['case_id']}, design {ev.get('design')})",
             f"Proposed action: {a['tool']} " + ", ".join(f"{k}={v}" for k, v in args.items() if k != "body"),
             f"The assistant's reason: {args.get('reason') or '(none given)'}",
             f"Asked by: {a['requested_by']}: {ev.get('request', '')}",
             f"Ticket: {ev.get('ticket_text', '')}",
             "What the assistant read: " + ("; ".join(ev.get("reads", [])) or "nothing"),
             "What the controls blocked: " + ("; ".join(ev.get("blocked", [])) or "nothing"),
             f"Reply draft: {ev.get('draft', '')}"]
    if args.get("body"):
        lines.append(f"E-mail text: {args['body']}")
    lines.append("Check the order and the policy yourself. Approve or reject with a reason.")
    if a["status"] != "pending":
        lines.append(f"Decided: {a['status']} by {a['decided_by']} ({a['decided_role']}): {a['reason']}")
    return "\n".join(lines)


def decide(world, approval_id: str, approver: str, approve: bool, reason: str) -> str:
    """Approve (and run) or reject one waiting proposal. Returns a message for the person."""
    from .tools import check_write
    if not reason or not reason.strip():
        return "Give a reason for your decision (--reason). A decision with no reason cannot be reviewed later."
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
        world.log(approver, a["tenant"], "review", "disagreed", approval=approval_id, tool=a["tool"], reason=reason)
        return f"{approval_id} rejected. Your disagreement with the assistant is logged."
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
