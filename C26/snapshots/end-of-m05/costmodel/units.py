"""Unit economics, scenarios and sensitivity (Module 3, lesson 3).

- fixed cost:    paid even with no questions (the database server, the API replica that waits)
- variable cost: grows with the questions and documents (tokens, requests, logs, data out)
- cost per tenant = fixed cost shared equally + variable cost by the tenant's share of questions
"""

from dataclasses import dataclass

from .costs import VARIABLE, monthly
from .inputs import SCENARIOS


@dataclass(frozen=True)
class Units:
    total: float
    fixed: float
    variable: float
    questions: float
    per_question_variable: float
    per_question_all: float
    per_document_change: float
    per_tenant: dict           # tenant name -> US$ per month
    tenants: int


def units(demand, design, m, p, scenario="base", month=0, **kw) -> Units:
    costs, w = monthly(demand, design, m, p, scenario, month, **kw)
    total = sum(costs.values())
    variable = sum(v for k, v in costs.items() if k in VARIABLE)
    fixed = total - variable
    doc = costs["Model tokens: ingestion"] + costs["Model tokens: summaries"] + costs["Compute: ingestion worker"]
    q_var = variable - doc
    per_tenant = {name: fixed / w.tenants + q_var * q / w.questions_per_month + doc / w.tenants
                  for name, q in w.questions_by_tenant.items()}
    return Units(total, fixed, variable, w.questions_per_month, q_var / w.questions_per_month,
                 total / w.questions_per_month,
                 doc / w.document_changes_per_month if w.document_changes_per_month else 0.0,
                 per_tenant, w.tenants)


def unit_table(u: Units, title: str) -> str:
    lines = [title,
             f"  total                        US$ {u.total:>10,.2f} per month (fixed {u.total and u.fixed / u.total:.0%}, "
             f"variable {u.total and u.variable / u.total:.0%})",
             f"  per question (variable only) US$ {u.per_question_variable:>10.6f}",
             f"  per question (everything)    US$ {u.per_question_all:>10.6f}",
             f"  per document change          US$ {u.per_document_change:>10.6f} (embed + summary + worker)"]
    for name, usd in u.per_tenant.items():
        lines.append(f"  {name:<28} US$ {usd:>10,.2f} per month")
    return "\n".join(lines)


def scenarios(demand, design, m, p, months=(0, 12)) -> str:
    lines = ["Scenarios (US$ per month)", f"  {'':<10}" + "".join(f"{s:>12}" for s in SCENARIOS)]
    for month in months:
        us = [units(demand, design, m, p, s, month) for s in SCENARIOS]
        lines.append(f"  {'month ' + str(month):<10}" + "".join(f"{u.total:>12,.2f}" for u in us)
                     + f"   ({us[1].tenants} tenants)")
        lines.append(f"  {'per tenant':<10}" + "".join(f"{u.total / u.tenants:>12,.2f}" for u in us))
    return "\n".join(lines)


CASES = (
    ("base", {}),
    ("usage x 2", {"usage": 2.0}),
    ("answers 2x longer", {"answer_length": 2.0}),
    ("chat-strong for every answer", {"answer_model": "strong"}),
    ("all prices +20%", {"price_factor": 1.2}),
)


def sensitivity(demand, design, m, p, scenario="base") -> list[dict]:
    base = units(demand, design, m, p, scenario)
    rows = []
    for name, kw in CASES:
        u = units(demand, design, m, p, scenario, **kw)
        rows.append({"case": name, "total": u.total, "change": u.total / base.total - 1,
                     "per_question": u.per_question_all, "per_tenant": u.total / u.tenants})
    return rows


def sensitivity_table(rows: list[dict]) -> str:
    lines = ["Sensitivity (base scenario, month 0)",
             f"  {'what if':<30} {'US$/month':>10} {'change':>8} {'per question':>13} {'per tenant':>11}"]
    for r in rows:
        lines.append(f"  {r['case']:<30} {r['total']:>10,.2f} {r['change']:>+8.0%} {r['per_question']:>13.6f} "
                     f"{r['per_tenant']:>11,.2f}")
    return "\n".join(lines)
