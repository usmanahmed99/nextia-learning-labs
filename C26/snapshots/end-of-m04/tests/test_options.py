import pytest
from helpers import pack

from costmodel.buildbuy import buildbuy_table, database_options, load_labour, model_options
from costmodel.options import answer_cost_per_question, batching_table, caching_table, routing_rows, routing_table


def test_routing_compares_three_designs_on_one_workload():
    d, g, m, p = pack()
    rows = {r["model"]: r for r in routing_rows(d, g, m, p)}
    assert set(rows) == {"small", "strong", "routed"}
    assert rows["small"]["usd_per_question"] < rows["routed"]["usd_per_question"] < rows["strong"]["usd_per_question"]
    assert rows["strong"]["p95_s"] > rows["small"]["p95_s"]


def test_the_measured_result_the_lesson_is_about():
    d, g, m, p = pack()
    rows = {r["model"]: r for r in routing_rows(d, g, m, p)}
    # On these 67 questions the strong model was not better: routing added cost, not quality.
    assert rows["strong"]["correct_share"] <= rows["small"]["correct_share"]
    assert rows["routed"]["correct_share"] == pytest.approx(rows["small"]["correct_share"])
    assert "chat-small only" in routing_table(list(rows.values())).splitlines()[-1]


def test_routed_cost_is_small_plus_the_escalated_share_of_strong():
    d, g, m, p = pack()
    share = m["routed_escalation_share"].value
    assert answer_cost_per_question(m, p, "routed") == pytest.approx(
        answer_cost_per_question(m, p, "small") + share * answer_cost_per_question(m, p, "strong"))


def test_caching_saves_money_but_not_the_median_wait_below_half():
    d, g, m, p = pack()
    text = caching_table(d, g, m, p)
    assert "ASSUMPTION" in text and "does not change until more than half" in text


def test_batching_saves_time_not_money():
    d, g, m, p = pack()
    assert m["embed_one_call_per_document_s"].value < m["embed_one_call_per_chunk_s_per_document"].value
    assert "the same tokens and the same cost" in batching_table(m, p)


def test_the_cheapest_machine_is_not_the_cheapest_total():
    d, g, m, p = pack()
    managed, own = database_options(p, load_labour())
    assert managed["machine"] < own["machine"]          # here the managed server is cheaper anyway
    assert own["people"] > own["machine"]                # and people's time is the biggest part


def test_a_self_hosted_model_pays_off_only_at_large_volume():
    d, g, m, p = pack()
    mo = model_options(m, p, load_labour(), 43_950)
    assert mo["own_total"] > 10 * mo["api"]
    assert mo["break_even_questions"] > 1_000_000
    assert "not measured" in buildbuy_table(m, p, load_labour(), 43_950)
