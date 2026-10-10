"""Decision scorers on a tiny made-up example (every value visible), then on the saved baseline."""

from types import SimpleNamespace as NS

import pytest

from harness.scorers.decisions import needs_human_counts, team_accuracy


def case(cid, team, needs):
    return NS(case_id=cid, expected=NS(team=team, needs_human=needs))


def out(team, needs):
    return NS(answer={"team": team, "needs_human": needs})


def test_tiny_example():
    cases = [case("a", "delivery", True), case("b", "returns", False), case("c", "payment", False),
             case("d", "warranty", True), case("e", "", True)]
    outputs = {"a": out("delivery", True), "b": out("delivery", True), "c": out("payment", False),
               "d": out("warranty", False), "e": out("account", True)}
    assert team_accuracy(cases, outputs) == (3, 4)          # "e" has no team to score
    n = needs_human_counts(cases, outputs)
    assert (n.tp, n.fp, n.fn, n.tn) == (2, 1, 1, 1)
    assert n.precision == pytest.approx(2 / 3) and n.recall == pytest.approx(2 / 3)


def test_a_missing_answer_counts_as_not_sent_to_a_person():
    n = needs_human_counts([case("a", "delivery", True)], {"a": NS(answer=None)})
    assert (n.tp, n.fn) == (0, 1)
