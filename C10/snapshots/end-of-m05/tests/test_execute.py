"""Side effects and retries (the Module 4 completion check): interrupt before and after a mock write,
resume without a duplicate and without bypassing approval. The failures are SIMULATED by the mock services."""

from resolver.approval import decide
from resolver.execute import Interrupted, execute
from resolver.systems import Faults

from .test_approval import proposed

LATE_FEE = {"tool": "request_refund", "order_id": "LK-793996", "amount": 9.95, "reason_code": "RFD-LATE"}
REFUND_DOUBLE = {"tool": "request_refund", "order_id": "LK-645223", "amount": 45.95, "reason_code": "RFD-DOUBLE",
                 "payment_id": "PAY-645223-2"}


def approved(task_id, actions):
    s = proposed(task_id, actions)
    decide(s, True, "Amira", "agent")
    return s


def test_interrupt_before_the_write_then_resume(world):
    s, w = approved("T-90104", [LATE_FEE]), world("T-90104")
    try:
        execute(s, w, interrupt="before-write")
    except Interrupted:
        pass
    assert w.changes() == [] and s.operations[0].status == "pending"
    execute(s, w)                                           # resume
    assert len(w.changes()) == 1 and s.status == "done"


def test_interrupt_after_the_write_then_resume_reconciles(world):
    s, w = approved("T-90104", [LATE_FEE]), world("T-90104")
    try:
        execute(s, w, interrupt="after-write")
    except Interrupted:
        pass
    assert len(w.changes()) == 1 and s.operations[0].status == "pending"   # written, not yet recorded
    execute(s, w)                                           # resume: the operation ID finds it
    assert len(w.changes()) == 1 and s.status == "done"
    assert any(e.kind == "reconcile" and e.detail["found"] for e in s.events)


def test_a_timeout_after_the_write_is_reconciled_not_repeated(world):
    s = approved("T-90603", [REFUND_DOUBLE])
    w = world("T-90603", Faults([{"tool": "request_refund", "mode": "timeout_after_write", "times": 1}]))
    execute(s, w)
    assert len(w.changes()) == 1 and s.status == "done"


def test_just_calling_it_again_refunds_twice(world):
    """Tomas's shortcut: retry a timed-out refund with a new request. The customer gets 9.95 twice."""
    s = approved("T-90104", [LATE_FEE])
    w = world("T-90104", Faults([{"tool": "request_refund", "mode": "timeout_after_write", "times": 1}]))
    execute(s, w, naive=True)
    refunds = [c for c in w.changes() if c["tool"] == "request_refund"]
    assert [r["amount"] for r in refunds] == [9.95, 9.95]


def test_a_timeout_before_the_write_is_retried_with_the_same_id(world):
    label = {"tool": "create_return_label", "order_id": "LK-645334", "sku": "LADDER-3", "reason": "change_of_mind"}
    s = approved("T-90604", [label])
    w = world("T-90604", Faults([{"tool": "create_return_label", "mode": "timeout_before_write", "times": 1}]))
    execute(s, w)
    assert len(w.changes()) == 1 and s.operations[0].attempts == 2


def test_a_service_that_is_down_once_is_retried(world):
    fee = {"tool": "request_refund", "order_id": "LK-645556", "amount": 9.95, "reason_code": "RFD-LATE"}
    s = approved("T-90606", [fee])
    w = world("T-90606", Faults([{"tool": "request_refund", "mode": "unavailable", "times": 1}]))
    execute(s, w)
    assert len(w.changes()) == 1


def test_a_refused_write_goes_to_a_person_with_no_change(world):
    reship = {"tool": "reship_item", "order_id": "LK-645445", "sku": "TROWEL", "quantity": 1}
    s = approved("T-90605", [reship])
    w = world("T-90605", Faults([{"tool": "reship_item", "mode": "denied", "times": 99}]))
    execute(s, w)
    assert s.status == "handed_to_person" and w.changes() == []


def test_running_the_same_approved_proposal_twice_changes_nothing_more(world):
    s, w = approved("T-90104", [LATE_FEE]), world("T-90104")
    execute(s, w)
    s2 = approved("T-90104", [LATE_FEE])        # a second run of the same ticket and decision
    execute(s2, w)
    assert len(w.changes()) == 1 and s2.operations[0].result.get("repeated")
