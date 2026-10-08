"""Compare the scores of a running service with the scores the model gave in training.

    python parity/check_parity.py http://127.0.0.1:8000 bundles/escalation-1.0.0

Sends every parity case of the bundle to POST /v1/score and compares the
served score with expected_score, the score that the training code gave the
same ticket. A difference larger than the tolerance means the serving path
does something that training did not do (training-serving skew).
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import pandas as pd

TOLERANCE = 1e-9


def as_json_value(value):
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def served_score(url: str, ticket: dict, key: str | None) -> float:
    request = urllib.request.Request(
        f"{url}/v1/score",
        data=json.dumps(ticket).encode(),
        headers={"Content-Type": "application/json", **({"X-API-Key": key} if key else {})},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["score"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--tolerance", type=float, default=TOLERANCE)
    args = parser.parse_args()

    cases = pd.read_csv(args.bundle / "parity_cases.csv", keep_default_na=False, na_values=[""],
                        dtype={"priority": "Int64", "word_count": "Int64", "customer_tenure_days": "Int64",
                               "prior_tickets_90d": "Int64", "created_hour": "Int64",
                               "prior_escalations_90d": "Int64"})
    key = os.environ.get("API_KEY")
    failed = 0
    print(f"{'case':8} {'ticket':9} {'expected':>10} {'served':>10} {'difference':>10}")
    for row in cases.to_dict("records"):
        expected = row.pop("expected_score")
        case = row.pop("case")
        ticket = {k: as_json_value(v) for k, v in row.items()}
        served = served_score(args.url, ticket, key)
        difference = abs(served - expected)
        ok = difference <= args.tolerance
        failed += not ok
        print(f"{case:8} {row['ticket_id']:9} {expected:10.6f} {served:10.6f} {difference:10.1e}"
              f"{'' if ok else '  FAIL'}")
    print(f"{len(cases) - failed} of {len(cases)} cases match within {args.tolerance:g}.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
