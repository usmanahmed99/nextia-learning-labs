import json
import subprocess
import sys

import pandas as pd

from tests.conftest import TICKET


def run_batch(tmp_path, rows):
    source = tmp_path / "tickets.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, "-m", "escalation.batch", str(source), str(out)],
                            capture_output=True, text=True)
    return result, out


def test_bad_rows_are_set_aside(tmp_path):
    rows = [{**TICKET, "ticket_id": f"T-{120000 + i}"} for i in range(40)]
    rows[5]["priority"] = "high"
    result, out = run_batch(tmp_path, rows)
    assert result.returncode == 0, result.stderr
    assert len(pd.read_csv(out / "scores.csv")) == 39
    rejected = pd.read_csv(out / "rejected.csv")
    assert rejected.to_dict("records")[0]["row"] == 7
    assert json.loads((out / "summary.json").read_text())["status"] == "done"


def test_too_many_bad_rows_fail_the_job(tmp_path):
    rows = [{**TICKET, "ticket_id": f"T-{120000 + i}", "created_hour": 25} for i in range(10)]
    result, out = run_batch(tmp_path, rows)
    assert result.returncode == 1
    assert not (out / "scores.csv").exists()
    assert len(pd.read_csv(out / "rejected.csv")) == 10
