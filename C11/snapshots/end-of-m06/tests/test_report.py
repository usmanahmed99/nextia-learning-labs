"""The report is rebuilt from saved outputs, the same every time, and names the cases behind its numbers."""

from harness.dataset import load_cases
from harness.report import build
from harness.run import find_run, load_outputs


def _report():
    b, c = find_run("baseline"), find_run("candidate")
    return build(load_cases(split="holdout"), b, load_outputs(b), c, load_outputs(c), "holdout")


def test_the_report_is_reproducible():
    assert _report() == _report()


def test_the_report_names_the_blocker_and_its_case():
    text = _report()
    assert "**Do not ship.**" in text
    assert "| T-65663 | No valid answer on a critical case." in text
