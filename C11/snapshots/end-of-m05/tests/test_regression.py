"""Regression checks: the release rules as tests on the saved baseline. They run on every change.

If a change to a scorer or to the data breaks one of these, the change is wrong (or the rule must be
changed on purpose, with a reason)."""

import pytest

from harness.dataset import load_cases
from harness.run import find_run, load_outputs
from harness.scorers.criteria import check_reply

BASELINE = load_outputs(find_run("baseline"))
CASES = [c for c in load_cases(split="all") if c.split != "contaminated"]


@pytest.mark.parametrize("case", [c for c in CASES if c.expected.rule == "H1"], ids=lambda c: c.case_id)
def test_every_safety_ticket_goes_to_a_person(case):
    assert BASELINE[case.case_id].answer["needs_human"] is True


@pytest.mark.parametrize("case", [c for c in CASES if c.critical], ids=lambda c: c.case_id)
def test_no_forbidden_reply_on_a_critical_case(case):
    failed = [r.code for r in check_reply(case, BASELINE[case.case_id]) if r.kind == "must_not" and not r.passed]
    assert failed == []
