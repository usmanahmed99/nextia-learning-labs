"""Percent agreement and Cohen's kappa: the worked example of the lesson, by hand."""

import pytest

from harness.agreement import chance_agreement, cohens_kappa, percent_agreement, within_one


def test_worked_example():
    # 10 replies: both "ok" on 6, both "bad" on 1, rater 1 "ok" / rater 2 "bad" on 2, the opposite on 1
    a = ["ok"] * 6 + ["bad"] + ["ok"] * 2 + ["bad"]
    b = ["ok"] * 6 + ["bad"] + ["bad"] * 2 + ["ok"]
    assert percent_agreement(a, b) == pytest.approx(0.70)
    assert chance_agreement(a, b) == pytest.approx(0.8 * 0.7 + 0.2 * 0.3)
    assert cohens_kappa(a, b) == pytest.approx(0.08 / 0.38)


def test_agreement_by_chance_alone_gives_kappa_zero():
    a = ["no"] * 9 + ["yes"]
    b = ["no"] * 9 + ["yes"]
    assert cohens_kappa(a, b) == pytest.approx(1.0)
    c = ["no"] * 10
    assert percent_agreement(a, c) == pytest.approx(0.9)  # looks good
    assert cohens_kappa(a, c) == pytest.approx(0.0)       # but it is what chance gives


def test_within_one_point():
    assert within_one([5, 4, 1], [4, 2, 1]) == pytest.approx(2 / 3)
