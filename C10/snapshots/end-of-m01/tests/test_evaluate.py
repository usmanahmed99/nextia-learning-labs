"""Scoring a proposal (constructed cases): the outcome and exactly the right actions."""

from resolver.data import load_task
from resolver.evaluate import score
from resolver.runner import new_state
from resolver.schema import parse_resolution


def proposed(task_id, actions, outcome="resolve"):
    s = new_state(load_task(task_id), "agent", "chat-small", "test")
    flat = [dict(a, reason=a.get("reason") or a.get("reason_code")) for a in actions]
    s.proposal = parse_resolution({"outcome": outcome, "rule": "W", "actions": flat, "reply": "ok", "reason": "test"})
    return s


LABEL = {"tool": "create_return_label", "order_id": "LK-640218", "sku": "RUG-W", "reason": "change_of_mind"}


def test_the_right_action_is_right():
    assert score(load_task("T-90101"), proposed("T-90101", [LABEL])).proposal_ok


def test_an_extra_action_is_wrong():
    reship = {"tool": "reship_item", "order_id": "LK-640218", "sku": "RUG-W", "quantity": 1}
    assert not score(load_task("T-90101"), proposed("T-90101", [LABEL, reship])).proposal_ok


def test_an_accepted_alternative_outcome_is_right_without_actions():
    assert score(load_task("T-80009"), proposed("T-80009", [], "ask_customer")).proposal_ok


def test_a_stopped_run_goes_to_a_person():
    s = new_state(load_task("T-80001"), "agent", "chat-small", "test")
    s.stop_reason = "max_steps"
    sc = score(load_task("T-80001"), s)
    assert sc.outcome == "hand_to_person" and sc.proposal_ok
