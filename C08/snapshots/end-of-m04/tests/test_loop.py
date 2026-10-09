import json

from assistant.context import build_request
from assistant.loop import Limits, run_tool_loop
from assistant.orders import OrderBook
from assistant.providers import Completion
from assistant.schema import response_format
from assistant.tools import TOOLS

BOOK = OrderBook()


def request_for(ticket, model="chat-small"):
    return build_request(ticket, model, "v2", response_format(), TOOLS)


def test_a_recorded_loop_looks_up_the_customers_own_order(mock, tickets):
    t = tickets["T-80008"]
    result = run_tool_loop(mock.complete, request_for(t), t.customer_id, BOOK)
    assert [s.outcome for s in result.steps] == ["ok"] and not result.stopped
    assert result.looked_up["LK-581106"]["status"] == "shipped" and len(result.completions) == 2


def test_the_model_asked_for_another_customers_order_and_the_application_refused(mock, tickets):
    t = tickets["T-80001"]  # the neighbour's order: a real recorded proposal
    result = run_tool_loop(mock.complete, request_for(t), t.customer_id, BOOK)
    assert [(json.loads(s.arguments)["order_id"], s.outcome) for s in result.steps] == [
        ("LK-615204", "refused: other_customer")]
    assert result.looked_up == {} and result.completion is not None


def test_the_model_invented_an_order_id(mock, tickets):
    t = tickets["T-65059"]  # the ticket names no order; the model asked for LK-000000 (real recording)
    result = run_tool_loop(mock.complete, request_for(t), t.customer_id, BOOK)
    assert [(s.arguments, s.outcome) for s in result.steps] == [('{"order_id":"LK-000000"}', "refused: not_found")]


def test_a_repeated_call_stops_the_loop(mock, tickets):
    t = tickets["T-80008"]  # constructed: the model asks for the same order twice
    result = run_tool_loop(mock.complete, request_for(t, "constructed-example"), t.customer_id, BOOK)
    assert result.stopped == "repeated_call" and result.completion is None
    assert [s.outcome for s in result.steps] == ["ok", "stopped: repeated call"]


def tool_call(order_id):
    data = {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
        {"id": order_id, "type": "function", "function": {"name": "get_order", "arguments": json.dumps(
            {"order_id": order_id})}}]}}]}
    return Completion.from_response(data, 0.0)


def test_the_step_limit_stops_a_model_that_never_answers(tickets):
    ids = iter(["LK-581106", "LK-000001", "LK-000002", "LK-000003", "LK-000004"])
    result = run_tool_loop(lambda request: tool_call(next(ids)), {"messages": []}, "C-81265", BOOK, Limits(max_steps=3))
    assert result.stopped == "max_steps" and len(result.steps) == 3


def test_the_time_limit_stops_a_slow_loop():
    ticks = iter([0.0, 30.0, 61.0])
    ids = iter(["LK-581106", "LK-000001"])
    result = run_tool_loop(lambda request: tool_call(next(ids)), {"messages": []}, "C-81265", BOOK,
                           Limits(max_seconds=60), clock=lambda: next(ticks))
    assert result.stopped == "time"
