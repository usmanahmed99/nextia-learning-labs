"""Ranking measures: a 5-question worked example by hand, then the saved search results."""

import pytest

from harness.scorers.retrieval import (evaluate, hit_at, load_rankings, precision_at, recall_at,
                                       reciprocal_rank)

# Five questions, top 5 results each; r = relevant passage, x = not relevant.
WORKED = [
    (["r1", "x", "x", "x", "x"], {"r1"}),          # found at rank 1
    (["x", "x", "r1", "x", "x"], {"r1"}),          # found at rank 3
    (["x", "r1", "x", "r2", "x"], {"r1", "r2"}),   # both found, first at rank 2
    (["x", "x", "x", "x", "x"], {"r1"}),           # not found
    (["r2", "x", "x", "x", "x"], {"r1", "r2"}),    # one of two found, at rank 1
]


def test_worked_example():
    assert [hit_at(r, rel, 5) for r, rel in WORKED] == [1, 1, 1, 0, 1]
    assert [recall_at(r, rel, 5) for r, rel in WORKED] == [1, 1, 1, 0, 0.5]
    assert [precision_at(r, rel, 5) for r, rel in WORKED] == [0.2, 0.2, 0.4, 0, 0.2]
    rr = [reciprocal_rank(r, rel, 5) for r, rel in WORKED]
    assert rr == pytest.approx([1, 1 / 3, 1 / 2, 0, 1])
    assert sum(rr) / 5 == pytest.approx(0.5667, abs=1e-4)


def test_saved_search_results():
    data = load_rankings()
    assert len(data["questions"]) == 67
    keyword, rerank = evaluate(data, "keyword", 5), evaluate(data, "rerank", 5)
    assert keyword["questions"] == 59
    assert round(keyword["hit"], 3) == 0.831 and round(rerank["hit"], 3) == 0.898
    assert round(keyword["mrr"], 3) == 0.655 and round(rerank["mrr"], 3) == 0.831
    assert rerank["recall"] > keyword["recall"]
