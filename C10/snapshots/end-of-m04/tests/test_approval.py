"""The approval boundary: nothing runs without the right person's approval of the exact proposal."""

import pytest

from resolver.approval import ApprovalError, approval_request, decide, required_role
from resolver.data import load_task
from resolver.execute import ExecutionRefused, execute
from resolver.runner import new_state
from resolver.schema import parse_resolution
from resolver.state import Evidence


def proposed(task_id, actions, outcome="resolve"):
    task = load_task(task_id)
    s = new_state(task, "agent", "chat-small", f"{task_id}-test")
    s.evidence.append(Evidence(step=1, tool="get_order", arguments={}, ok=True, code="ok",
                               order_ids=[a["order_id"] for a in actions]))
    flat = [dict(a, reason=a.get("reason") or a.get("reason_code")) for a in actions]
    s.proposal = parse_resolution({"outcome": outcome, "rule": "W", "actions": flat, "reply": "ok", "reason": "test"})
    s.status = "waiting_approval"
    return s


REFUND_119 = {"tool": "request_refund", "order_id": "LK-507862", "amount": 119.0, "reason_code": "RFD-DOUBLE",
              "payment_id": "PAY-507862-2"}


def test_nothing_runs_without_approval(world):
    s = proposed("T-65273", [REFUND_119])
    with pytest.raises(ExecutionRefused):
        execute(s, world("T-65273"))


def test_the_refund_limit_decides_who_may_approve():
    s = proposed("T-65273", [REFUND_119])
    assert required_role(s) == "team_lead"
    with pytest.raises(ApprovalError):
        decide(s, True, "Amira", "agent")
    decide(s, True, "Priya", "team_lead")
    assert s.status == "executing"


def test_a_proposal_changed_after_approval_does_not_run(world):
    s = proposed("T-65273", [REFUND_119])
    decide(s, True, "Grace", "grace")
    s.proposal.actions[0].amount = 238.0                  # changed after the approval
    with pytest.raises(ExecutionRefused):
        execute(s, world("T-65273"))
    assert world("T-65273").changes() == []


def test_a_rejection_writes_nothing(world):
    s = proposed("T-65273", [REFUND_119])
    decide(s, False, "Grace", "grace", "the second charge is a hold")
    assert s.status == "handed_to_person"
    with pytest.raises(ExecutionRefused):
        execute(s, world("T-65273"))


def test_the_approver_sees_the_exact_action():
    text = approval_request(proposed("T-65273", [REFUND_119]))
    assert "request_refund       LK-507862  119.00 CAD  RFD-DOUBLE  payment PAY-507862-2" in text
    assert "team lead" in text and "nothing has happened yet" in text
