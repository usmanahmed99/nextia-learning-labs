import csv
import json

import pytest
from helpers import pack

from costmodel.costs import monthly
from costmodel.export import write_csv, write_explorer


def test_the_csv_gives_the_same_totals_as_the_calculator(tmp_path):
    d, g, m, p = pack()
    write_csv(d, g, m, p, tmp_path / "costs.csv")
    rows = list(csv.DictReader(open(tmp_path / "costs.csv", encoding="utf-8")))
    assert len(rows) == 84
    base0 = sum(float(r["usd_per_month"]) for r in rows if r["scenario"] == "base" and r["month"] == "0")
    assert base0 == pytest.approx(sum(monthly(d, g, m, p)[0].values()), abs=0.01)


def test_the_explorer_data_has_one_row_per_usage_multiplier(tmp_path):
    d, g, m, p = pack()
    message = write_explorer(d, g, m, p, tmp_path / "explorer.json")
    data = json.loads((tmp_path / "explorer.json").read_text())
    assert [r["usage"] for r in data["rows"]] == data["multipliers"]
    assert "not 2" in message
