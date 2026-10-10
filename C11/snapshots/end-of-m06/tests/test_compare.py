"""The bootstrap and the paired difference, on small made-up lists."""

import pytest

from harness.compare import bootstrap_mean, paired_difference, wins_losses


def test_the_same_seed_gives_the_same_interval():
    values = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1]
    assert bootstrap_mean(values) == bootstrap_mean(values)
    ci = bootstrap_mean(values)
    assert ci.value == pytest.approx(0.7) and ci.low < 0.7 < ci.high


def test_more_cases_give_a_narrower_interval():
    small, large = bootstrap_mean([1, 0] * 10), bootstrap_mean([1, 0] * 200)
    assert (large.high - large.low) < (small.high - small.low)


def test_paired_difference_and_the_cases_behind_it():
    base = {"a": 1, "b": 1, "c": 0, "d": 0}
    cand = {"a": 1, "b": 0, "c": 1, "d": 1}
    assert paired_difference(base, cand).value == pytest.approx(0.25)
    assert wins_losses(base, cand) == {"better": ["c", "d"], "worse": ["b"], "same": ["a"]}
