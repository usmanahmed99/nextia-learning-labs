"""Export the cost model for a spreadsheet (costs.csv) and for the course's explorer (explorer.json).

A spreadsheet that reads costs.csv gives the same totals as the calculator: the CSV holds every
driver for every scenario and month, so you can check each sum by hand.
"""

import csv
import json

from .costs import DRIVERS, VARIABLE, monthly
from .inputs import SCENARIOS

MULTIPLIERS = (0.25, 0.5, 1, 2, 4, 8, 16)


def write_csv(demand, design, m, p, path) -> str:
    with open(path, "w", newline="", encoding="utf-8") as f:
        out = csv.writer(f)
        out.writerow(["scenario", "month", "driver", "fixed_or_variable", "usd_per_month"])
        for scenario in SCENARIOS:
            for month in (0, 12):
                costs, _ = monthly(demand, design, m, p, scenario, month)
                for d in DRIVERS:
                    out.writerow([scenario, month, d, "variable" if d in VARIABLE else "fixed", f"{costs[d]:.4f}"])
    return f"Wrote {path.name}: {len(SCENARIOS) * 2 * len(DRIVERS)} rows (3 scenarios x 2 months x {len(DRIVERS)} drivers)"


def explorer_data(demand, design, m, p) -> dict:
    rows = []
    for x in MULTIPLIERS:
        costs, w = monthly(demand, design, m, p, "base", 0, usage=x)
        rows.append({"usage": x, "questions_per_month": round(w.questions_per_month),
                     "tenants": w.tenants, "total": round(sum(costs.values()), 2),
                     "per_tenant": round(sum(costs.values()) / w.tenants, 2),
                     "drivers": {k: round(v, 4) for k, v in costs.items()}})
    return {"scenario": "base", "month": 0, "multipliers": list(MULTIPLIERS), "rows": rows,
            "variable": sorted(VARIABLE)}


def write_explorer(demand, design, m, p, path) -> str:
    data = explorer_data(demand, design, m, p)
    path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    one, two = data["rows"][2], data["rows"][3]
    return (f"Wrote {path.name}: usage x1 US${one['total']:,.2f} per month, x2 US${two['total']:,.2f} "
            f"({two['total'] / one['total']:.2f} times, not 2)")
