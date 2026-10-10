"""The mock services: idempotent writes, reconciliation, the service's own checks, simulated failures."""

import pytest

from resolver.systems import Faults, InvalidRequest, ServiceTimeout


def test_the_same_operation_id_writes_once(world):
    w = world("T-90104")
    first = w.request_refund("op-1", "LK-793996", 9.95, "RFD-LATE")
    again = w.request_refund("op-1", "LK-793996", 9.95, "RFD-LATE")
    assert again["repeated"] and again["refund_id"] == first["refund_id"]
    assert len(w.changes()) == 1


def test_a_timeout_after_the_write_hides_a_change_that_happened(world):
    w = world("T-90603", Faults([{"tool": "request_refund", "mode": "timeout_after_write", "times": 1}]))
    with pytest.raises(ServiceTimeout):
        w.request_refund("op-2", "LK-645223", 45.95, "RFD-DOUBLE", "PAY-645223-2")
    assert len(w.changes()) == 1                      # it happened
    assert w.operation("op-2")["amount"] == 45.95     # and reconciliation can find it
    assert w.operation("op-unknown") is None


def test_the_payment_service_refuses_more_than_was_paid(world):
    w = world()
    with pytest.raises(InvalidRequest):
        w.request_refund("op-3", "LK-793996", 500.00, "RFD-LATE")
    with pytest.raises(InvalidRequest):   # the extra charge of LK-641876 was already refunded
        w.request_refund("op-4", "LK-641876", 73.95, "RFD-DOUBLE", "PAY-641876-2")


def test_reship_checks_the_order_and_the_stock(world):
    w = world()
    with pytest.raises(InvalidRequest):
        w.reship_item("op-5", "LK-641210", "FEEDER", 1)      # out of stock
    with pytest.raises(InvalidRequest):
        w.reship_item("op-6", "LK-644445", "POT-TC3", 2)     # only 1 ordered
    assert w.changes() == []


def test_seed_rows_are_not_changes(world):
    assert world().changes() == []
