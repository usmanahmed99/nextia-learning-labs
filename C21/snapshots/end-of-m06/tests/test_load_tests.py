"""The load-test tools of Module 6: shapes, configurations, cost per ticket."""

import json
import subprocess
import sys
from pathlib import Path

from scripts import compare, cost

ROOT = Path(__file__).resolve().parent.parent

# Locust patches the standard library when it is imported, so the shapes are read in a
# separate Python process.
READ_SHAPES = """
import json, sys
sys.path.insert(0, "loadtest")
import ramp, steady, burst, soak
print(json.dumps({m.__name__: [c for c in vars(m).values() if isinstance(c, type)
                  and hasattr(c, "stages") and c.stages][0].stages
                  for m in (ramp, steady, burst, soak)}))
"""


def test_the_load_shapes():
    out = subprocess.run(
        [sys.executable, "-c", READ_SHAPES], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    shapes = json.loads(out.strip().splitlines()[-1])
    assert shapes["steady"] == [[70, 4]]
    assert shapes["burst"] == [[20, 2], [35, 20], [80, 2]]  # ten times more for 15 s
    assert [users for _, users in shapes["ramp"]] == [2, 4, 8, 12, 16]
    assert shapes["soak"][-1][0] == 600
    for stages in shapes.values():
        times = [t for t, _ in stages]
        assert times == sorted(times)


def test_a_configuration_is_a_name_and_settings():
    name, env = compare.parse_config("queue, 2 workers:INTAKE_MODE=queue,WORKERS=2")
    assert name == "queue, 2 workers" and env == {"INTAKE_MODE": "queue", "WORKERS": "2"}


def test_median_and_range_of_passes():
    passes = [{"p95_ms": 900}, {"p95_ms": 1100}, {"p95_ms": 1000}, {"p95_ms": None}]
    assert compare.median_and_range(passes, "p95_ms") == {"median": 1000, "min": 900, "max": 1100}


def test_cost_per_ticket_from_the_tokens(make_api, conn):
    api = make_api(intake_mode="async")
    for _ in range(2):
        api.post(
            "/v1/tickets",
            json={"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments."},
        )
    c = cost.per_ticket(conn, None)
    assert c["tickets"] == 2
    tasks = {r["task"]: r for r in c["tasks"]}
    assert set(tasks) == {"classify", "draft_reply", "embed"}
    expected = sum(
        (
            r["tokens_in"] * {"chat-small": 0.10, "embed-small": 0.02}[r["model"]]
            + r["tokens_out"] * {"chat-small": 0.50, "embed-small": 0.0}[r["model"]]
        )
        / 1e6
        for r in c["tasks"]
    )
    assert abs(c["ai_usd"] - expected) < 1e-12
    assert 0 < c["ai_usd"] / 2 < 0.001  # well under a tenth of a cent per ticket
