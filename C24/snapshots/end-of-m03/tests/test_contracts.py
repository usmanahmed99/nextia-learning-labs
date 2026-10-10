"""Strict contracts and business rules: a call must have the right shape before it runs, and a refund
may not be more than what is still refundable on the order."""

from tests._helpers import SECURE, WEAK, run, session
from support_assistant.runner import fresh_world


def test_a_bad_order_id_is_refused_before_the_tool_runs():
    w = fresh_world()
    t = w.ticket("T-24002")
    for bad in ("LK-640436; DROP TABLE orders", "../LK-640436", "lk-640436"):
        out = run("get_order", {"order_id": bad}, WEAK, session(), t, w)
        assert out.event.code == "invalid_arguments" and not out.event.allowed


def test_an_extra_field_or_a_negative_amount_is_refused():
    w = fresh_world()
    t = w.ticket("T-24002")
    extra = run("issue_refund", {"order_id": "LK-640436", "amount": 5, "approved_by": "usr-grace"}, SECURE,
                session(), t, w)
    negative = run("issue_refund", {"order_id": "LK-640436", "amount": -50}, SECURE, session(), t, w)
    assert extra.event.code == negative.event.code == "invalid_arguments"
    assert "not valid" in negative.text


def test_a_refund_over_what_is_still_refundable_is_refused():
    w = fresh_world()
    t = w.ticket("T-24011")   # LK-702219: 216.00 paid, 9.95 already refunded
    owner = session(role="owner", sub="usr-grace")
    over = run("issue_refund", {"order_id": "LK-702219", "amount": 210.0}, SECURE, owner, t, w)
    assert "still refundable" in over.proposal.refused_reason
    ok = run("issue_refund", {"order_id": "LK-702219", "amount": 206.05}, SECURE, owner, t, w)
    assert not ok.proposal.refused_reason
