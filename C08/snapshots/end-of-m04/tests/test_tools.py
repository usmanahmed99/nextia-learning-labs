import pytest

from assistant.orders import OrderBook
from assistant.tools import ToolRefused, get_order, run_tool

BOOK = OrderBook()


def test_a_customer_gets_their_own_order():
    order = get_order("LK-581106", "C-81265", BOOK)
    assert order["status"] == "shipped" and "customer_id" not in order


def test_another_customers_order_is_refused_like_a_missing_one():
    with pytest.raises(ToolRefused) as other:
        get_order("LK-615204", "C-20417", BOOK)   # the neighbour's order (ticket T-80001)
    with pytest.raises(ToolRefused) as missing:
        get_order("LK-000001", "C-20417", BOOK)
    assert other.value.code == "other_customer" and missing.value.code == "not_found"
    assert str(other.value).replace("LK-615204", "X") == str(missing.value).replace("LK-000001", "X")


@pytest.mark.parametrize("arguments", ['{"order_id": "LK-55190"}', '{"order_id": "1 OR 1=1"}', "not json",
                                       '{"order_id": "LK-615204", "customer_id": "C-38852"}'])
def test_bad_arguments_are_refused_before_the_database(arguments):
    result, outcome = run_tool("get_order", arguments, "C-20417", BOOK)
    assert result["ok"] is False and outcome == "refused: invalid_argument"


def test_an_unknown_tool_is_refused():
    result, outcome = run_tool("refund_order", '{"order_id": "LK-428830"}', "C-44702", BOOK)
    assert outcome == "refused: unknown_tool"
