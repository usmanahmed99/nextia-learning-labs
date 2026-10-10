import pytest
from helpers import pack

from costmodel.costs import DRIVERS, HOURS_PER_MONTH, cost_table, monthly


def test_every_driver_has_a_cost():
    d, g, m, p = pack()
    costs, _ = monthly(d, g, m, p)
    assert list(costs) == list(DRIVERS)
    assert all(v >= 0 for v in costs.values())


def test_the_database_server_is_its_hourly_price_for_a_month():
    d, g, m, p = pack()
    costs, _ = monthly(d, g, m, p)
    assert costs["Database server"] == pytest.approx(p["pg_b1ms_hour"].value * HOURS_PER_MONTH)
    assert costs["Database storage"] == pytest.approx(32 * p["pg_storage_gb_month"].value)


def test_answer_tokens_are_questions_times_tokens_times_price():
    d, g, m, p = pack()
    costs, w = monthly(d, g, m, p, answer_model="small")
    asked = w.questions_per_month * (1 - g.get("cache_hit_share", "base"))
    per = (m["answer_small_tokens_in"].value * p["chat_small_input"].value
           + m["answer_small_tokens_out"].value * p["chat_small_output"].value) / 1e6
    assert costs["Model tokens: answers"] == pytest.approx(asked * per)


def test_free_amounts_make_small_drivers_zero():
    d, g, m, p = pack()
    costs, w = monthly(d, g, m, p)
    assert costs["Logs"] == 0 and costs["Network out"] == 0 and costs["Requests"] == 0


def test_prices_scale_but_free_amounts_do_not():
    d, g, m, p = pack()
    base = sum(monthly(d, g, m, p)[0].values())
    more = sum(monthly(d, g, m, p, price_factor=1.2)[0].values())
    assert more == pytest.approx(base * 1.2, rel=0.01)


def test_the_table_names_the_biggest_driver():
    d, g, m, p = pack()
    costs, _ = monthly(d, g, m, p)
    text = cost_table(costs, "t")
    assert "Total" in text and f"Biggest driver: {max(costs, key=costs.get)}" in text
