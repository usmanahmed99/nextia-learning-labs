"""Review design: the reviewer sees the proposed action with its evidence and the assistant's reason,
every decision needs a reason, and a rejection is logged as a disagreement with the assistant."""

import json

from support_assistant import approvals
from support_assistant.assistant import run_case
from support_assistant.data import load_tasks
from support_assistant.runner import fresh_world
from tests.scripted import Scripted

STEPS = [("", [("get_order", json.dumps({"order_id": "LK-640436"}))]),
         ("", [("issue_refund", json.dumps({"order_id": "LK-640436", "amount": 89.0, "reason": "damaged on arrival"}))]),
         ("Sorry about the damage. We have asked for a refund of 89 dollars.", [])]


def _queued():
    w = fresh_world()
    st = run_case(load_tasks()["TASK-02"], Scripted(list(STEPS)).complete, w, "scripted", "secure")
    return w, st.proposals[0].approval_id


def test_the_review_shows_the_action_its_evidence_and_the_reason():
    w, approval_id = _queued()
    text = approvals.review_text(w, approval_id)
    assert "Proposed action: issue_refund" in text and "amount=89.0" in text
    assert "The assistant's reason: damaged on arrival" in text
    assert "order LK-640436" in text and "Reply draft: Sorry about the damage" in text


def test_a_decision_needs_a_reason():
    w, approval_id = _queued()
    assert "Give a reason" in approvals.decide(w, approval_id, "usr-grace", True, "  ")
    assert approvals.get(w, approval_id)["status"] == "pending"


def test_a_rejection_is_logged_as_a_disagreement():
    w, approval_id = _queued()
    approvals.decide(w, approval_id, "usr-grace", False, "the photo shows no damage")
    events = [e for e in w.audit_rows() if e["action"] == "review"]
    assert events and events[0]["result"] == "disagreed" and events[0]["detail"]["approval"] == approval_id
    assert approvals.get(w, approval_id)["reason"] == "the photo shows no damage"
