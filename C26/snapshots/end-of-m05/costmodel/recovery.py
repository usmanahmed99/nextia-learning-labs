"""Recovery objectives (Module 5, lesson 2): can a backup plan meet the RTO and the RPO?

RTO (recovery time objective): how long the service may be down.
RPO (recovery point objective): how much recent data you may lose, as time.
Recovery time = detect + decide + a new server + restore the data + check it.
"""

from pathlib import Path

from .inputs import ROOT, InputError, check_range, pick, read_toml

STEPS = ("detect_minutes", "decide_minutes", "new_server_minutes", "check_minutes", "point_in_time_rpo_minutes")


def load_recovery(path: Path | None = None) -> dict:
    d = read_toml(path or ROOT / "design.toml").get("recovery")
    if d is None:
        raise InputError("design.toml has no [recovery] section (Module 5, lesson 2)")
    out = {k: check_range(k, d.get(k)) for k in STEPS}
    out["rto_target_minutes"] = float(d["rto_target_minutes"])
    out["rpo_target_minutes"] = float(d["rpo_target_minutes"])
    return out


def plans(r: dict, m: dict, database_gb: float, scenario: str = "base") -> list[dict]:
    restore_min = database_gb * 1000 / m["restore_mb_per_s"].value / 60
    human = sum(pick(r[k], scenario) for k in ("detect_minutes", "decide_minutes", "check_minutes"))
    server = pick(r["new_server_minutes"], scenario)
    out = [
        {"plan": "nightly dump to file storage", "rpo_minutes": 24 * 60, "rto_minutes": human + server + restore_min},
        {"plan": "managed point-in-time restore", "rpo_minutes": pick(r["point_in_time_rpo_minutes"], scenario),
         "rto_minutes": human + server + restore_min},
    ]
    for p in out:
        p["meets_rto"] = p["rto_minutes"] <= r["rto_target_minutes"]
        p["meets_rpo"] = p["rpo_minutes"] <= r["rpo_target_minutes"]
    return out


def recovery_table(r: dict, m: dict, database_gb: float, scenario: str = "base") -> str:
    restore_s = database_gb * 1000 / m["restore_mb_per_s"].value
    lines = [f"Recovery ({scenario}): targets RTO {r['rto_target_minutes']:.0f} min, RPO {r['rpo_target_minutes']:.0f} min; "
             f"database {database_gb * 1000:,.0f} MB restores in about {restore_s:,.1f} s (measured rate, a laptop)",
             f"  {'plan':<32} {'RPO min':>8} {'RTO min':>8}  meets both?"]
    for p in plans(r, m, database_gb, scenario):
        ok = "yes" if p["meets_rto"] and p["meets_rpo"] else "no (" + ", ".join(
            x for x, good in (("RPO", p["meets_rpo"]), ("RTO", p["meets_rto"])) if not good) + ")"
        lines.append(f"  {p['plan']:<32} {p['rpo_minutes']:>8,.0f} {p['rto_minutes']:>8,.0f}  {ok}")
    lines.append("Most of the recovery time is people and a new server, not copying data. Test the restore to know.")
    return "\n".join(lines)
