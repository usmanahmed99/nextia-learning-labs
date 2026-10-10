"""The required permission tests (Module 6 completion check): another customer's order can be neither read
nor written, even with an approval; a write never runs without one."""

import pytest

from resolver.approval import decide
from resolver.execute import ExecutionRefused, execute
from resolver.tools import run_read

from .test_approval import proposed


def test_reading_another_customers_order_is_refused(world):
    assert run_read("get_order", {"order_id": "LK-644334"}, "C-54223", world()).code == "other_customer"


def test_writing_another_customers_order_is_refused_even_when_approved(world):
    s = proposed("T-90503", [{"tool": "reship_item", "order_id": "LK-644334", "sku": "HAMMOCK", "quantity": 1}])
    decide(s, True, "Grace", "grace")
    with pytest.raises(ExecutionRefused):
        execute(s, world("T-90503"))
    assert world("T-90503").changes() == []


def test_no_write_without_approval(world):
    s = proposed("T-90101", [{"tool": "create_return_label", "order_id": "LK-640218", "sku": "RUG-W",
                              "reason": "change_of_mind"}])
    with pytest.raises(ExecutionRefused):
        execute(s, world("T-90101"))
