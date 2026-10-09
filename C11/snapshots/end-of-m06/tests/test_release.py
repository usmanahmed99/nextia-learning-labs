"""Blockers fail a release whatever the average (real runs, and the one constructed practice reply)."""

from harness.dataset import load_cases
from harness.release import blockers, decide
from harness.run import find_run, load_outputs


def _run(name):
    run = find_run(name)
    return run.run_id, load_outputs(run)


def test_the_candidate_is_blocked_on_the_holdout_set():
    cases = load_cases(split="holdout")
    (bid, bout), (cid, cout) = _run("baseline"), _run("candidate")
    d = decide(cases, bid, bout, cid, cout)
    assert not d.ship
    assert [(b.case_id, b.code) for b in d.blockers] == [("T-65663", "no_answer_critical")]  # a safety ticket, cut off


def test_the_baseline_has_no_blocker():
    rid, out = _run("baseline")
    for split in ("dev", "holdout"):
        assert blockers(rid, load_cases(split=split), out) == []


def test_the_constructed_permission_failure_is_caught():
    rid, out = _run("practice")
    found = {(b.case_id, b.code) for b in blockers(rid, load_cases(split="dev"), out)}
    assert {("T-81034", "missed_access"), ("T-81034", "other_customer")} <= found


def test_a_review_wins_over_a_phrase_rule():
    rid, out = _run("practice")
    review = {(rid, "T-81034", "other_customer"): {"verdict": "not_a_failure", "by": "test"}}
    found = {(b.case_id, b.code) for b in blockers(rid, load_cases(split="dev"), out, review)}
    assert ("T-81034", "other_customer") not in found and ("T-81034", "missed_access") in found
