"""Demand: what we expect the tenants' people to do (demand.toml).

Each demand value is a range [low, base, high] and has evidence: "verified: <how we know>"
or "assumed: <why we chose it>". An assumption is not a mistake; a hidden one is.
"""

from dataclasses import dataclass
from pathlib import Path

from .inputs import ROOT, InputError, check_range, pick, read_toml

TENANT_FIELDS = (
    "staff_users",                 # help-desk staff who ask the assistant
    "staff_questions_per_day",     # questions per staff user per working day
    "customers_per_day",           # customers who ask at least one question in a day
    "customer_questions_per_day",  # questions per such customer
    "documents",                   # documents in the tenant's collection
    "words_per_document",          # average length of a document
    "document_changes_per_month",  # new or updated documents (each one is ingested again)
    "user_growth_per_month",       # 0.02 = 2% more questions every month
)
SETTING_FIELDS = ("peak_hour_share", "peak_minute_factor")


@dataclass(frozen=True)
class Tenant:
    key: str
    name: str
    joins_in_month: int
    values: dict          # field -> (low, base, high)
    evidence: dict        # field -> "verified: ..." or "assumed: ..."

    def get(self, field: str, scenario: str) -> float:
        return pick(self.values[field], scenario)


@dataclass(frozen=True)
class Demand:
    days_per_month: int
    settings: dict        # field -> (low, base, high)
    settings_evidence: dict
    tenants: list

    def setting(self, field: str, scenario: str) -> float:
        return pick(self.settings[field], scenario)


def _evidence(where: str, fields, evidence: dict) -> dict:
    out = {}
    for f in fields:
        text = str(evidence.get(f, "")).strip()
        if not text.startswith(("verified:", "assumed:")):
            raise InputError(f"{where}: '{f}' needs evidence that starts with 'verified:' or 'assumed:'")
        out[f] = text
    return out


def load_demand(path: Path | None = None) -> Demand:
    path = path or ROOT / "demand.toml"
    data = read_toml(path)
    s = data.get("settings", {})
    if "days_per_month" not in s:
        raise InputError("demand.toml: [settings] needs days_per_month")
    settings = {f: check_range(f, s.get(f)) for f in SETTING_FIELDS}
    settings_evidence = _evidence("[settings]", SETTING_FIELDS, s.get("evidence", {}))
    tenants = []
    for key, t in data.get("tenants", {}).items():
        values = {f: check_range(f"{key}.{f}", t.get(f)) for f in TENANT_FIELDS}
        if values["user_growth_per_month"][2] > 1:
            raise InputError(f"{key}.user_growth_per_month is a share: 0.02 means 2%")
        tenants.append(Tenant(key, t.get("name", key), int(t.get("joins_in_month", 0)), values,
                              _evidence(f"[tenants.{key}]", TENANT_FIELDS, t.get("evidence", {}))))
    if not tenants:
        raise InputError("demand.toml has no tenants yet")
    return Demand(int(s["days_per_month"]), settings, settings_evidence, tenants)


def active(demand: Demand, month: int) -> list[Tenant]:
    """The tenants that use the assistant in this month (month 0 = now)."""
    return [t for t in demand.tenants if t.joins_in_month <= month]


def questions_per_day(t: Tenant, scenario: str, month: int = 0, usage: float = 1.0) -> float:
    """Staff questions + customer questions, grown for the months since the tenant joined."""
    base = (t.get("staff_users", scenario) * t.get("staff_questions_per_day", scenario)
            + t.get("customers_per_day", scenario) * t.get("customer_questions_per_day", scenario))
    growth = (1 + t.get("user_growth_per_month", scenario)) ** max(0, month - t.joins_in_month)
    return base * growth * usage


def evidence_counts(demand: Demand) -> tuple[int, int]:
    texts = [*demand.settings_evidence.values(), *(e for t in demand.tenants for e in t.evidence.values())]
    verified = sum(1 for e in texts if e.startswith("verified:"))
    return verified, len(texts) - verified


def demand_table(demand: Demand, month: int = 0) -> str:
    lines = [f"Demand in month {month} (questions per day; low / base / high)"]
    total = [0.0, 0.0, 0.0]
    for t in active(demand, month):
        q = [questions_per_day(t, s, month) for s in ("low", "base", "high")]
        total = [a + b for a, b in zip(total, q, strict=True)]
        lines.append(f"  {t.name:<16} {q[0]:>8,.0f} {q[1]:>8,.0f} {q[2]:>8,.0f}")
    lines.append(f"  {'All tenants':<16} {total[0]:>8,.0f} {total[1]:>8,.0f} {total[2]:>8,.0f}")
    peak = [total[i] * demand.setting("peak_hour_share", s) for i, s in enumerate(("low", "base", "high"))]
    lines.append(f"  {'Busiest hour':<16} {peak[0]:>8,.0f} {peak[1]:>8,.0f} {peak[2]:>8,.0f}")
    verified, assumed = evidence_counts(demand)
    lines.append(f"Evidence: {verified} values verified, {assumed} assumed (check the assumed ones first)")
    return "\n".join(lines)
