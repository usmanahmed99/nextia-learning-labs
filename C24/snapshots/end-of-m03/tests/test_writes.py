"""Writes wait for a person and respect the role, and the output check holds a leaking answer.
These controls arrive when the course constrains the consequences of a mistake."""

import json

from support_assistant import approvals
from support_assistant.assistant import run_case
from support_assistant.context import check_answer
from support_assistant.data import load_tasks, made_up_secrets
from support_assistant.runner import fresh_world
from tests._helpers import SECURE, WEAK, run, session
from tests.scripted import Scripted


def test_write_needs_approval_and_respects_role_limits():
    w = fresh_world()
    t = w.ticket("T-24002")   # customer C-50533, order LK-640436 (delivered, 89 dollars)
    proposed = run("issue_refund", {"order_id": "LK-640436", "amount": 89.0}, SECURE, session(), t, w)
    assert proposed.proposal is not None and not proposed.proposal.executed and not proposed.proposal.refused_reason
    big = run("issue_refund", {"order_id": "LK-640436", "amount": 149.0}, SECURE, session(), t, w)
    assert big.proposal.refused_reason and "limit" in big.proposal.refused_reason


def test_read_only_member_may_not_write():
    w = fresh_world()
    t = w.ticket("T-24011")
    out = run("issue_refund", {"order_id": "LK-702219", "amount": 9.95}, SECURE,
              session(role="read_only", sub="usr-omar"), t, w)
    assert out.proposal.refused_reason


def test_email_only_to_the_address_on_file():
    w = fresh_world()
    t = w.ticket("T-24002")   # C-50533 = priti.shah@mail.example
    good = run("send_email", {"to": "priti.shah@mail.example", "subject": "x", "body": "y"}, SECURE, session(), t, w)
    assert not good.proposal.refused_reason
    bad = run("send_email", {"to": "attacker@evil.example", "subject": "x", "body": "y"}, SECURE, session(), t, w)
    assert bad.proposal.refused_reason


def test_weak_write_runs_at_once():
    w = fresh_world(redact_log=False)
    t = w.ticket("T-24002")
    out = run("issue_refund", {"order_id": "LK-640436", "amount": 500.0}, WEAK, session(), t, w)
    assert out.proposal.executed and out.proposal.execution_id
    assert len(w.changes()["refunds"]) == 2   # the seed's one refund, and this one


def _queued(amount, task="TASK-02", order_id="LK-640436"):
    """Run a task with a model that proposes a refund; return the world and the approval ID."""
    case = load_tasks()[task]
    steps = [("", [("issue_refund", json.dumps({"order_id": order_id, "amount": amount, "reason": "damaged"}))]),
             ("We have asked for a refund.", [])]
    w = fresh_world()
    st = run_case(case, Scripted(steps).complete, w, "scripted", "secure")
    return w, st.proposals[0].approval_id


def test_a_proposal_waits_in_the_database_until_a_person_decides():
    w, approval_id = _queued(89.0)
    assert approval_id and approvals.get(w, approval_id)["status"] == "pending"
    assert w.changes()["refunds"] == [r for r in w.changes()["refunds"] if r["approval_id"] is None]
    msg = approvals.decide(w, approval_id, "usr-sam", True, "damaged on arrival, photo in the ticket")
    assert "approved" in msg and approvals.get(w, approval_id)["status"] == "approved"
    assert any(r["approval_id"] == approval_id for r in w.changes()["refunds"])


def test_the_approver_needs_a_role_that_may_decide():
    w, approval_id = _queued(89.0)
    assert "read-only" in approvals.decide(w, approval_id, "usr-omar", True, "looks fine")
    assert "no membership" in approvals.decide(w, approval_id, "usr-ines", True, "looks fine")
    assert approvals.get(w, approval_id)["status"] == "pending"


def test_the_approvers_own_refund_limit_applies():
    w, approval_id = _queued(119.0, task="TASK-12", order_id="LK-507862")   # Grace (owner) asked
    assert "limit" in approvals.decide(w, approval_id, "usr-sam", True, "customer asked twice")
    assert "approved" in approvals.decide(w, approval_id, "usr-grace", True, "full refund, item lost")


def test_output_check_catches_secret_and_outside_link():
    assert check_answer("Here is the key " + made_up_secrets()[0])
    assert check_answer("Please open https://collector.attacker.example/p?x=1")
    assert check_answer("![pixel](https://collector.attacker.example/p.png)")
    assert check_answer("Your parcel ships 13 October. See https://help.larkfield.example/returns") == ""
