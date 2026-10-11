"""Growth plan (Module 5, lesson 3): month by month, which signal crosses its line first.

A growth plan is a list of steps, each started by a measured signal, not one big final design.
"""

from .costs import monthly
from .inputs import ROOT, read_toml


def load_growth(path=None) -> dict:
    return read_toml(path or ROOT / "design.toml")["growth"]


def timeline(demand, design, m, p, scenario="base", months=12) -> list[dict]:
    g = load_growth()
    rows = []
    for month in range(months + 1):
        costs, w = monthly(demand, design, m, p, scenario, month)
        tokens_per_question = m["answer_small_tokens_in"].value + m["answer_small_tokens_out"].value
        rows.append({
            "month": month, "tenants": w.tenants, "questions_per_day": w.questions_per_month / demand.days_per_month,
            "calls_share": w.model_calls_peak_minute / m["provider_quota_requests_per_minute"].value,
            "tokens_share": w.model_calls_peak_minute * tokens_per_question / m["provider_quota_tokens_per_minute"].value,
            "storage_share": (sum(w.storage_gb.values()) - w.storage_gb["files"] + w.storage_growth_gb_per_month * month)
            / design.database_storage_gb,
            "total": sum(costs.values()),
        })
    for r in rows:
        r["signals"] = [name for name, hit in (
            ("provider quota", max(r["calls_share"], r["tokens_share"]) >= g["quota_alert_share"]),
            ("database storage", r["storage_share"] >= g["storage_alert_share"]),
            ("budget", r["total"] >= g["budget_usd_per_month"])) if hit]
    return rows


def growth_table(rows: list[dict], scenario: str) -> str:
    lines = [f"Growth ({scenario}): busiest minute against the provider quota, storage, cost",
             f"  {'month':>5} {'tenants':>7} {'questions/day':>13} {'calls/quota':>11} {'tokens/quota':>12} "
             f"{'storage':>8} {'US$/month':>10}  signals"]
    for r in rows:
        lines.append(f"  {r['month']:>5} {r['tenants']:>7} {r['questions_per_day']:>13,.0f} {r['calls_share']:>11.0%} "
                     f"{r['tokens_share']:>12.0%} {r['storage_share']:>8.0%} {r['total']:>10,.2f}  "
                     + (", ".join(r["signals"]) or "-"))
    first = {}
    for r in rows:
        for s in r["signals"]:
            first.setdefault(s, r["month"])
    lines.append("First signal: " + (", ".join(f"{s} in month {mo}" for s, mo in first.items()) or "none in these months"))
    return "\n".join(lines)
