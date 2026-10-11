import pytest
from helpers import pack

from costmodel.workload import answer_seconds, compute, explain


def test_volume_is_questions_per_day_times_days():
    d, g, m, p = pack()
    w = compute(d, g, m, "base")
    assert w.questions_per_month == pytest.approx(sum(w.questions_by_tenant.values()))
    assert w.questions_per_month == pytest.approx(1465 * 30, rel=0.01)


def test_concurrency_is_arrival_rate_times_time_in_the_system():
    d, g, m, p = pack()
    w = compute(d, g, m, "base")
    assert w.in_flight_at_peak == pytest.approx(w.peak_per_second * w.seconds_in_system)
    assert w.seconds_in_system == pytest.approx(answer_seconds(m, "small"))
    assert w.in_flight_at_peak < 1        # far from "a million users"


def test_time_in_the_system_adds_the_measured_steps():
    d, g, m, p = pack()
    expected = m["question_embed_p50_s"].value + m["retrieval_rerank_s"].value + m["answer_small_p50_s"].value
    assert answer_seconds(m, "small") == pytest.approx(expected)
    assert answer_seconds(m, "strong") > answer_seconds(m, "small")


def test_doubling_usage_doubles_the_questions_but_not_the_documents():
    d, g, m, p = pack()
    one, two = compute(d, g, m, "base"), compute(d, g, m, "base", usage=2)
    assert two.questions_per_month == pytest.approx(2 * one.questions_per_month)
    assert two.documents == one.documents
    assert two.tokens["embed-small"]["in"] < 2 * one.tokens["embed-small"]["in"] + 1


def test_storage_grows_with_answers_and_document_changes():
    d, g, m, p = pack()
    w = compute(d, g, m, "base")
    assert w.storage_growth_gb_per_month > 0
    assert w.storage_gb["answers and logs in the database"] > w.storage_gb["files"]


def test_the_explanation_shows_every_step():
    d, g, m, p = pack()
    text = explain(compute(d, g, m, "base"), m)
    for step in ("questions per month", "in flight at the peak", "provider quota", "tokens per month", "storage growth"):
        assert step in text
