import pytest
from helpers import pack

from costmodel.units import scenarios, sensitivity, units


def test_cost_per_tenant_adds_up_to_the_total():
    d, g, m, p = pack()
    u = units(d, g, m, p)
    assert sum(u.per_tenant.values()) == pytest.approx(u.total)
    assert u.fixed + u.variable == pytest.approx(u.total)


def test_most_of_the_cost_is_fixed_at_this_size():
    d, g, m, p = pack()
    u = units(d, g, m, p)
    assert u.fixed > u.variable
    assert u.per_question_all > 5 * u.per_question_variable


def test_doubling_usage_does_not_double_the_cost():
    d, g, m, p = pack()
    one, two = units(d, g, m, p), units(d, g, m, p, usage=2)
    assert one.total < two.total < 1.5 * one.total
    assert two.per_question_all < one.per_question_all


def test_scenarios_are_ordered_and_tenants_share_the_fixed_cost():
    d, g, m, p = pack()
    low, base, high = (units(d, g, m, p, s).total for s in ("low", "base", "high"))
    assert low < base < high
    now, later = units(d, g, m, p, "base", 0), units(d, g, m, p, "base", 12)
    assert later.tenants == 4 and later.total / later.tenants < now.total / now.tenants
    assert "month 12" in scenarios(d, g, m, p)


def test_sensitivity_cases():
    d, g, m, p = pack()
    rows = {r["case"]: r for r in sensitivity(d, g, m, p)}
    assert rows["base"]["change"] == 0
    assert rows["all prices +20%"]["change"] == pytest.approx(0.2, abs=0.01)
    assert rows["chat-strong for every answer"]["change"] > rows["usage x 2"]["change"]
