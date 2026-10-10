"""Tenant and customer scope: the assistant for one ticket sees only that shop and that customer."""

import json

from support_assistant.assistant import run_case
from support_assistant.data import load_attacks
from support_assistant.evaluate import score_attack
from support_assistant.runner import fresh_world
from tests._helpers import SECURE, WEAK, run, session
from tests.scripted import Scripted


def test_cross_tenant_order_blocked_with_controls_allowed_without():
    w = fresh_world()
    t = w.ticket("T-24124")   # a Larkfield ticket
    weak = run("get_order", {"order_id": "BB-310002"}, WEAK, session(), t, w)
    assert weak.event.ok and weak.event.read_order_tenant == "bramble"
    safe = run("get_order", {"order_id": "BB-310002"}, SECURE, session(), t, w)
    assert not safe.event.ok and "No order" in safe.text


def test_order_of_another_customer_same_tenant_blocked():
    w = fresh_world()
    t = w.ticket("T-24124")
    out = run("get_order", {"order_id": "LK-640436"}, SECURE, session(), t, w)
    assert not out.event.ok


def test_cross_tenant_attack_blocked_under_secure_but_succeeds_at_start():
    case = load_attacks()["ATK-26"]
    steps = [("", [("get_order", json.dumps({"order_id": "BB-310002"}))]),
             ("Here is the order you asked about.", [])]
    for design, expect in (("start", True), ("secure", False)):
        model = Scripted(list(steps))
        st = run_case(case, model.complete, fresh_world(redact_log=(design == "start")), "scripted", design)
        assert score_attack(st, case, fresh_world())["success"] is expect, design
