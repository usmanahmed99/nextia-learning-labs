"""The read tools: permissions in code, failures as results (never exceptions), dates computed in code."""

import json

from resolver.systems import Faults
from resolver.tools import function_tools, run_read


def test_unknown_tool_is_refused(world):
    r = run_read("delete_order", {"order_id": "LK-640436"}, "C-50533", world())
    assert not r.ok and r.code == "unknown_tool"


def test_another_customers_order_looks_like_a_missing_one(world):
    w = world()
    other = run_read("get_order", {"order_id": "LK-615204"}, "C-20417", w)    # the neighbour's shed
    missing = run_read("get_order", {"order_id": "LK-000001"}, "C-20417", w)
    assert other.code == "other_customer" and missing.code == "not_found"
    assert other.error.replace("LK-615204", "X") == missing.error.replace("LK-000001", "X")   # nothing leaks
    assert not run_read("get_payments", {"order_id": "LK-615204"}, "C-20417", w).ok


def test_a_service_failure_is_a_result(world):
    w = world(faults=Faults([{"tool": "get_order", "mode": "timeout", "times": 1}]))
    first = run_read("get_order", {"order_id": "LK-645001"}, "C-55001", w)
    second = run_read("get_order", {"order_id": "LK-645001"}, "C-55001", w)
    assert not first.ok and first.code == "service_timeout"
    assert second.ok


def test_the_tools_compute_the_dates(world):
    w = world()
    assert run_read("get_order", {"order_id": "LK-643556"}, "C-53556", w).data["business_days_late"] == 5
    assert run_read("get_order", {"order_id": "LK-347101"}, "C-27560", w).data["business_days_late"] == 15
    assert run_read("get_order", {"order_id": "LK-643001"}, "C-53001", w).data["days_since_delivery"] == 30


def test_search_policy_returns_passages_with_versions(world):
    hits = run_read("search_policy", {"query": "hose reel warranty"}, "C-90825", world()).data
    assert hits[0]["title"].startswith("AquaFlow")            # the supplier passage with the hidden instruction
    assert all("version" in h for h in hits)


def test_the_model_sees_strict_schemas_and_no_customer_id():
    tools = function_tools()
    assert [t["function"]["name"] for t in tools] == ["get_order", "get_customer_orders", "get_payments",
                                                      "search_policy", "finish"]
    assert all(t["function"]["strict"] for t in tools)
    assert "customer" not in json.dumps(tools[0]["function"]["parameters"])
