"""The approval boundary: nothing is written until a person approves the exact proposal.

The approver sees the exact actions (tool, order, item, quantity, amount), who may approve them, the
evidence the tools returned, and the reply draft. The approval records WHAT was approved (a digest of the
actions): if the proposal changes afterwards, the approval no longer matches and nothing runs.
"""

from .schema import Refund
from .state import Approval, TaskState, proposal_digest

ROLES = ("agent", "team_lead", "grace")
LIMITS = {"agent": 100.00, "team_lead": 500.00, "grace": float("inf")}   # refund approval limits (policy)


class ApprovalError(Exception):
    pass


def required_role(state: TaskState) -> str:
    """Who may approve: refunds up to 100 dollars any agent, up to 500 a team lead, over 500 Grace."""
    biggest = max((a.amount for a in state.proposal.actions if isinstance(a, Refund)), default=0.0)
    for role in ROLES:
        if biggest <= LIMITS[role]:
            return role
    return "grace"


def describe(action) -> str:
    if action.tool == "create_return_label":
        fee = "free" if action.reason in ("damaged", "wrong_item") else "12.95 taken from the refund later"
        return f"create_return_label  {action.order_id}  {action.sku}  reason {action.reason} (return shipping: {fee})"
    if action.tool == "reship_item":
        return f"reship_item          {action.order_id}  {action.sku} x {action.quantity}"
    pay = f"  payment {action.payment_id}" if action.payment_id else ""
    return f"request_refund       {action.order_id}  {action.amount:.2f} CAD  {action.reason_code}{pay}"


def approval_request(state: TaskState) -> str:
    """The text the approver sees."""
    p = state.proposal
    lines = [f"Approval needed for run {state.run_id} (ticket {state.task_id})",
             f"Proposed by: {state.variant}, {state.model}. Rule: {p.rule}.", "", "Actions (nothing has happened yet):"]
    lines += [f"  {i}. {describe(a)}" for i, a in enumerate(p.actions, 1)]
    lines += ["", f"Who may approve: {required_role(state).replace('_', ' ')} or above", "",
              f"Why: {p.reason}", "", "Evidence the tools returned:"]
    for e in state.evidence:
        status = "ok" if e.ok else f"failed ({e.code})"
        lines.append(f"  step {e.step}: {e.tool} {e.arguments} -> {status}")
    lines += ["", "Reply draft (sent only after the team's check):", f"  {p.reply}"]
    return "\n".join(lines)


def decide(state: TaskState, approve: bool, approver: str, role: str, note: str = "") -> TaskState:
    if state.status != "waiting_approval" or state.proposal is None:
        raise ApprovalError(f"Run {state.run_id} is not waiting for approval (status: {state.status}).")
    if role not in ROLES:
        raise ApprovalError(f"Unknown role {role!r}: use agent, team_lead or grace.")
    need = required_role(state)
    if approve and ROLES.index(role) < ROLES.index(need):
        who = {"agent": "An agent", "team_lead": "A team lead", "grace": "Grace"}[role]
        need_who = {"agent": "an agent", "team_lead": "a team lead", "grace": "Grace"}[need]
        raise ApprovalError(f"{who} may not approve this: it needs {need_who} (refund approval limits).")
    state.approval = Approval(decision="approved" if approve else "rejected", approver=approver, role=role, note=note,
                              proposal_digest=proposal_digest(state.proposal))
    state.log("approval", state.approval.decision, approver=approver, role=role, note=note,
              digest=state.approval.proposal_digest)
    state.status = "executing" if approve else "handed_to_person"
    return state
