"""The loop always ends: step limit, time, cost, repeated calls, unknown tools, bad proposals, no recording.

The models here are SCRIPTED (constructed in tests/scripted.py), not recorded: they misbehave on purpose.
"""

from resolver.agent import run_agent
from resolver.data import load_task
from resolver.loop import Limits
from resolver.providers import MockProvider
from resolver.runner import new_state

from .scripted import Scripted, call, finish


def run(world, script, task_id="T-90103", limits=Limits(), **kw):
    task = load_task(task_id)
    state = new_state(task, "agent", "chat-small", "test-run")
    return run_agent(state, Scripted(script, **kw).complete, world(task_id), "tools", limits)


def test_a_normal_run_finishes(world):
    s = run(world, [[call("get_order", order_id="LK-640436")],
                    [finish("resolve", "W5", [{"tool": "reship_item", "order_id": "LK-640436", "sku": "PLANTER",
                                               "quantity": 1}])]])
    assert s.stop_reason == "finished" and s.proposal.actions[0].sku == "PLANTER"


def test_the_step_limit_stops_a_model_that_never_finishes(world):
    s = run(world, [[call("search_policy", query=f"returns {i}")] for i in range(20)], limits=Limits(max_steps=4))
    assert s.stop_reason == "max_steps" and s.step == 4 and s.proposal is None


def test_a_repeated_successful_call_stops_the_loop(world):
    s = run(world, [[call("get_order", order_id="LK-640436")]])      # the same call, again and again
    assert s.stop_reason == "repeated_call" and s.step == 2


def test_a_failed_call_may_be_tried_again(world):
    from resolver.systems import Faults
    task = load_task("T-90601")
    state = new_state(task, "agent", "chat-small", "test-run")
    w = world("T-90601", Faults([{"tool": "get_order", "mode": "timeout", "times": 1}]))
    s = run_agent(state, Scripted([[call("get_order", order_id="LK-645001")], [call("get_order", order_id="LK-645001")],
                                   [finish()]]).complete, w, "tools")
    assert s.stop_reason == "finished" and [e.ok for e in s.evidence] == [False, True]


def test_unknown_tools_end_the_loop(world):
    s = run(world, [[call("issue_refund_now", amount=500)]])
    assert s.stop_reason in ("too_many_errors", "repeated_call")
    assert all(e.code == "unknown_tool" for e in s.evidence)


def test_repeated_errors_end_the_loop(world):
    s = run(world, [[call("get_order", order_id=f"LK-00000{i}")] for i in range(1, 9)])
    assert s.stop_reason == "too_many_errors" and s.step == 3


def test_the_time_budget(world):
    s = run(world, [[call("search_policy", query=f"returns {i}")] for i in range(9)], latency_s=50,
            limits=Limits(max_seconds=120))
    assert s.stop_reason == "time" and s.step == 3


def test_the_spending_cap(world):
    s = run(world, [[call("search_policy", query=f"refund {i}")] for i in range(9)], tokens=(200_000, 1000),
            limits=Limits(max_cost_usd=0.05))
    assert s.stop_reason == "cost" and s.step == 3


def test_an_invalid_resolution_is_refused_and_explained(world):
    bad = finish("resolve", "W5", [])                                  # resolve without any action
    s = run(world, [[call("get_order", order_id="LK-640436")], [bad], [finish("hand_to_person", "W5")]])
    refused = [e for e in s.events if e.kind == "proposal" and not e.detail["accepted"]]
    assert refused and "at least one action" in refused[0].detail["problem"]
    assert s.stop_reason == "finished" and s.proposal.outcome == "hand_to_person"


def test_an_action_on_an_order_that_was_never_looked_up_is_refused(world):
    act = [{"tool": "request_refund", "order_id": "LK-640436", "amount": 89.0, "reason_code": "RFD-DAMAGE"}]
    s = run(world, [[finish("resolve", "W5", act)], [finish("hand_to_person", "W5")]])
    refused = [e for e in s.events if e.kind == "proposal" and not e.detail["accepted"]]
    assert "was not returned by a tool" in refused[0].detail["problem"]


def test_no_recording_stops_cleanly():
    from resolver.systems import World
    task = load_task("T-90103")
    state = new_state(task, "agent", "model-never-recorded", "test-run")
    s = run_agent(state, MockProvider().complete, World(ticket_id=task.task_id), "tools")
    assert s.stop_reason == "no_recording" and s.proposal is None
