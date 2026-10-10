"""Build versus buy (Module 4, lesson 3): list prices plus people's time.

A managed service costs more per hour of machine, and less per hour of people. The labour
values are ASSUMPTIONS in design.toml [labour]: set your own rate and hours.
"""

from pathlib import Path

from .costs import HOURS_PER_MONTH
from .inputs import ROOT, InputError, check_range, pick, read_toml
from .options import answer_cost_per_question

LABOUR = ("rate_per_hour", "managed_database_hours_per_month", "own_database_hours_per_month",
          "own_model_hours_per_month", "own_model_tokens_per_second")


def load_labour(path: Path | None = None) -> dict:
    d = read_toml(path or ROOT / "design.toml").get("labour")
    if d is None:
        raise InputError("design.toml has no [labour] section (Module 4, lesson 3)")
    values = {k: check_range(k, d.get(k)) for k in LABOUR}
    for k in LABOUR:
        if not str(d.get("evidence", {}).get(k, "")).startswith(("verified:", "assumed:")):
            raise InputError(f"design.toml: labour '{k}' needs evidence that starts with 'verified:' or 'assumed:'")
    return values


def database_options(p: dict, labour: dict, scenario: str = "base", storage_gb: float = 32) -> list[dict]:
    rate = pick(labour["rate_per_hour"], scenario)
    managed_machine = p["pg_b1ms_hour"].value * HOURS_PER_MONTH + storage_gb * p["pg_storage_gb_month"].value
    own_machine = p["vm_b2s_hour"].value * HOURS_PER_MONTH + p["disk_p10_month"].value
    return [
        {"option": "managed PostgreSQL (B1ms)", "machine": managed_machine,
         "people": pick(labour["managed_database_hours_per_month"], scenario) * rate},
        {"option": "PostgreSQL on your own VM (B2s)", "machine": own_machine,
         "people": pick(labour["own_database_hours_per_month"], scenario) * rate},
    ]


def model_options(m: dict, p: dict, labour: dict, questions_per_month: float, scenario: str = "base") -> dict:
    rate = pick(labour["rate_per_hour"], scenario)
    api = questions_per_month * answer_cost_per_question(m, p, "small")
    gpu = p["gpu_t4_hour"].value * HOURS_PER_MONTH
    people = pick(labour["own_model_hours_per_month"], scenario) * rate
    tps = pick(labour["own_model_tokens_per_second"], scenario)
    capacity = tps * 3600 * 24 * 30 / m["answer_small_tokens_out"].value   # answers a month if it wrote all day
    return {"api": api, "gpu": gpu, "people": people, "own_total": gpu + people,
            "break_even_questions": (gpu + people) / answer_cost_per_question(m, p, "small"),
            "own_capacity_questions": capacity}


def buildbuy_table(m, p, labour, questions_per_month, scenario="base") -> str:
    lines = [f"Build versus buy ({scenario}; machine = list prices, people = your labour assumptions)",
             f"  {'option':<34} {'machine':>9} {'people':>9} {'total':>9}  US$ per month"]
    for r in database_options(p, labour, scenario):
        lines.append(f"  {r['option']:<34} {r['machine']:>9,.2f} {r['people']:>9,.2f} {r['machine'] + r['people']:>9,.2f}")
    mo = model_options(m, p, labour, questions_per_month, scenario)
    lines += [f"  {'hosted model (chat-small, tokens)':<34} {mo['api']:>9,.2f} {0:>9,.2f} {mo['api']:>9,.2f}",
              f"  {'own model on a T4 GPU VM':<34} {mo['gpu']:>9,.2f} {mo['people']:>9,.2f} {mo['own_total']:>9,.2f}",
              f"The own model pays for itself above {mo['break_even_questions']:,.0f} questions a month "
              f"(now: {questions_per_month:,.0f}); one GPU writes at most about {mo['own_capacity_questions']:,.0f} "
              "answers a month at the ASSUMED speed, and its quality is not measured."]
    return "\n".join(lines)
