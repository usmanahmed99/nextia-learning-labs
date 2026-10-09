"""The known-good first run: the evaluation set is there and the command line works."""

import subprocess
import sys

from harness.dataset import PROJECT, load_cases


def test_the_evaluation_set_is_complete():
    cases = load_cases(split="all")
    assert len(cases) == 271
    assert [sum(c.split == s for c in cases) for s in ("dev", "holdout", "contaminated")] == [102, 98, 71]


def test_holdout_is_not_loaded_by_default():
    assert all(c.split != "holdout" for c in load_cases())


def test_cli_cases():
    out = subprocess.run([sys.executable, "-m", "harness", "cases"], cwd=PROJECT, capture_output=True, text=True,
                         check=True).stdout
    assert out.startswith("271 cases, dataset version ")
    assert "dev            102" in out
