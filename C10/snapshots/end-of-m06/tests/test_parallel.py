"""Parallel reads with an explicit merge rule; conflicting workers go to a person."""

import time

import pytest

from resolver.parallel import Conflict, gather, merge_proposals
from resolver.schema import parse_resolution


def test_parallel_reads_keep_the_order_and_save_time(world):
    calls = [("get_order", {"order_id": "LK-640763"}), ("get_order", {"order_id": "LK-640872"}),
             ("get_payments", {"order_id": "LK-640763"})]
    start = time.monotonic()
    results = gather(calls, "C-50866", world("T-90201"), delay_s=0.2)
    took = time.monotonic() - start
    assert [r.order_ids for r in results] == [["LK-640763"], ["LK-640872"], ["LK-640763"]]
    assert took < 0.5          # three simulated 0.2 s reads, at the same time


def res(actions, outcome="resolve"):
    flat = [dict(a, reason=a.get("reason") or a.get("reason_code")) for a in actions]
    return parse_resolution({"outcome": outcome, "rule": "W", "actions": flat, "reply": "r", "reason": "x"})


def test_workers_on_different_orders_merge():
    a = res([{"tool": "request_refund", "order_id": "LK-640763", "amount": 9.95, "reason_code": "RFD-LATE"}])
    b = res([], "reply_only")
    assert merge_proposals(a, b).actions == a.actions


def test_workers_that_disagree_about_one_order_conflict():
    a = res([{"tool": "request_refund", "order_id": "LK-640763", "amount": 9.95, "reason_code": "RFD-LATE"}])
    b = res([{"tool": "request_refund", "order_id": "LK-640763", "amount": 45.95, "reason_code": "RFD-LATE"}])
    with pytest.raises(Conflict):
        merge_proposals(a, b)
