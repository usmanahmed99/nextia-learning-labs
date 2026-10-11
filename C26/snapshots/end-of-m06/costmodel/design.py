"""The design's sizing choices and its operating assumptions (design.toml).

Choices are plain values (which database size, how many API replicas). Assumptions are ranges
[low, base, high] with evidence, as in demand.toml.
"""

from dataclasses import dataclass
from pathlib import Path

from .inputs import ROOT, InputError, check_range, pick, read_toml

ASSUMPTIONS = (
    "busy_hours_per_day",      # hours a day when the API replica is busy (active), not idle
    "log_kb_per_question",     # log data written per question (request log, trace, audit line)
    "retry_share",             # share of model calls that are sent again (timeouts, 429)
    "cache_hit_share",         # share of questions answered from the answer cache
    "versions_kept",           # versions of each document kept in file storage
    "response_overhead_bytes",  # bytes of a response besides the answer text (JSON, headers)
    "backup_size_factor",      # backup storage / database size (full backups and changes kept)
)
DESIGNS = ("small", "strong", "routed")


@dataclass(frozen=True)
class Design:
    answer_model: str          # small | strong | routed
    database_price: str        # a key of prices.toml, for example pg_b1ms_hour
    database_storage_gb: float
    api_replicas: int
    api_vcpu: float
    api_memory_gib: float
    worker_vcpu: float
    worker_memory_gib: float
    assumptions: dict          # name -> (low, base, high)
    evidence: dict

    def get(self, name: str, scenario: str) -> float:
        return pick(self.assumptions[name], scenario)


def load_design(path: Path | None = None) -> Design:
    path = path or ROOT / "design.toml"
    d = read_toml(path)
    try:
        answers, db, api, worker, a = d["answers"], d["database"], d["api"], d["worker"], d["assumptions"]
        design = Design(
            answer_model=answers["model"], database_price=db["price"], database_storage_gb=float(db["storage_gb"]),
            api_replicas=int(api["min_replicas"]), api_vcpu=float(api["vcpu"]), api_memory_gib=float(api["memory_gib"]),
            worker_vcpu=float(worker["vcpu"]), worker_memory_gib=float(worker["memory_gib"]),
            assumptions={n: check_range(n, a.get(n)) for n in ASSUMPTIONS},
            evidence={n: str(a.get("evidence", {}).get(n, "")) for n in ASSUMPTIONS},
        )
    except KeyError as e:
        raise InputError(f"design.toml: {e.args[0]} is missing") from None
    if design.answer_model not in DESIGNS:
        raise InputError(f"design.toml: answers.model must be one of {', '.join(DESIGNS)}")
    for n, text in design.evidence.items():
        if not text.startswith(("verified:", "assumed:")):
            raise InputError(f"design.toml: '{n}' needs evidence that starts with 'verified:' or 'assumed:'")
    if design.assumptions["cache_hit_share"][2] >= 1 or design.assumptions["retry_share"][2] >= 1:
        raise InputError("design.toml: cache_hit_share and retry_share are shares below 1")
    return design
