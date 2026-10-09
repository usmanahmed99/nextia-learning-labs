"""The simulated production log: what the summary shows."""

from harness.feedback import load_log, review_sample, summary


def test_the_log_is_simulated_and_complete():
    rows = load_log()
    assert len(rows) == 1270 and all(r["simulated"] for r in rows)


def test_drift_appears_in_week_3():
    s = summary(load_log())
    new = s["new topic (not in the evaluation set) by week"]
    assert new[1] == 0 and new[2] == 0 and new[3] > 0.1


def test_the_review_sample_is_fixed():
    rows = load_log()
    assert review_sample(rows) == review_sample(rows) and len(review_sample(rows)) == 40
