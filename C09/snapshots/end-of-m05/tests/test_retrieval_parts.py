"""Filters, cosine similarity and reciprocal rank fusion on tiny examples with every value visible."""

from types import SimpleNamespace

import numpy as np
import pytest

from policy_assistant.dense import cosine, search
from policy_assistant.filters import Filters
from policy_assistant.hybrid import rrf
from policy_assistant.lexical import Hit


def chunk(access="public", start="2025-03-01", end=""):
    return SimpleNamespace(access=access, effective_from=start, effective_to=end)


def test_date_filter_keeps_the_version_in_force():
    v3, v4 = chunk(start="2025-03-01", end="2026-10-31"), chunk(start="2026-11-01")
    assert Filters(as_of="2026-10-20").allows(v3) and not Filters(as_of="2026-10-20").allows(v4)
    assert not Filters(as_of="2026-11-05").allows(v3) and Filters(as_of="2026-11-05").allows(v4)
    assert Filters(as_of="2026-10-31").allows(v3)                 # the last day is included
    assert Filters().allows(v3) and Filters().allows(v4)          # no date: every version


def test_access_filter_and_missing_label():
    assert Filters(audience="staff").allows(chunk("staff"))
    assert not Filters(audience="public").allows(chunk("staff"))
    assert not Filters(audience="public").allows(chunk(""))      # no label: treated as staff
    with pytest.raises(ValueError):
        Filters(audience="everyone")


def test_cosine_tiny_example():
    assert cosine(np.array([1.0, 0.0]), np.array([2.0, 0.0])) == pytest.approx(1.0)    # same direction
    assert cosine(np.array([1.0, 0.0]), np.array([0.0, 3.0])) == pytest.approx(0.0)    # unrelated
    assert cosine(np.array([3.0, 4.0]), np.array([4.0, 3.0])) == pytest.approx(0.96)   # (12 + 12) / (5 x 5)


def test_dense_search_order_and_filter():
    matrix = np.array([[1, 0], [0.8, 0.6], [0, 1]], dtype=np.float32)
    hits = search(np.array([1, 0.1]), matrix, ["a", "b", "c"], k=2)
    assert [h.id for h in hits] == ["a", "b"]
    assert [h.id for h in search(np.array([1, 0.1]), matrix, ["a", "b", "c"], 2, allowed=lambda i: i != "a")] == ["b", "c"]


def test_rrf_worked_example():
    keywords = [Hit("A", 9.1, 1), Hit("C", 7.0, 2)]
    vectors = [Hit("D", 0.9, 1), Hit("B", 0.8, 2), Hit("A", 0.7, 3)]
    fused = rrf([keywords, vectors], k=4)
    assert fused[0].id == "A" and fused[0].score == pytest.approx(1 / 61 + 1 / 63, abs=1e-6)   # 0.0323
    assert [h.id for h in fused[1:]] == ["D", "B", "C"] or [h.id for h in fused[1:]] == ["D", "C", "B"]
    assert fused[1].score == pytest.approx(1 / 61, abs=1e-6)
