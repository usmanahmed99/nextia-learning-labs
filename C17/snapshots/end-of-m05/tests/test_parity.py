"""The served scores equal the training scores for every parity case."""

import pandas as pd
import pytest

from tests.conftest import BUNDLE

INTS = ["priority", "word_count", "customer_tenure_days", "prior_tickets_90d", "created_hour", "prior_escalations_90d"]
CASES = pd.read_csv(BUNDLE / "parity_cases.csv", keep_default_na=False, na_values=[""], dtype={c: "Int64" for c in INTS})


def as_json(row: dict) -> dict:
    return {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in row.items()}


@pytest.mark.parametrize("row", CASES.to_dict("records"), ids=lambda r: f"{r['case']}-{r['ticket_id']}")
def test_served_score_matches_training(client, row):
    expected = row.pop("expected_score")
    row.pop("case")
    served = client.post("/v1/score", json=as_json(row)).json()["score"]
    assert served == pytest.approx(expected, abs=1e-9)
