"""The cost model: monthly cost by driver (Module 3, lesson 2).

cost of a driver = quantity per month x price per unit. Each line below says which quantity
(from workload.py) and which price (from prices.toml) it multiplies. Free allowances in the
price list (the first 5 GB of logs, the first 100 GB of data out, the Container Apps free
grant) are taken off before the price is applied.
"""

from .demand import Demand
from .design import Design
from .workload import Workload, compute

DRIVERS = (
    "Model tokens: answers", "Model tokens: question embeddings", "Model tokens: ingestion",
    "Model tokens: summaries", "Retries", "Database server", "Database storage", "Database backups",
    "File storage", "Compute: API", "Compute: ingestion worker", "Requests", "Logs", "Network out",
)
VARIABLE = {"Model tokens: answers", "Model tokens: question embeddings", "Model tokens: ingestion",
            "Model tokens: summaries", "Retries", "Requests", "Logs", "Network out", "Compute: ingestion worker"}
HOURS_PER_MONTH = 730          # the hours that cloud price lists use for a month (365 x 24 / 12)
SECONDS_PER_DAY = 86_400


def _per_million(tokens: float, price: float) -> float:
    return tokens / 1e6 * price


def _after_free(quantity: float, free: float) -> float:
    return max(0.0, quantity - free)


def monthly(demand: Demand, design: Design, m: dict, p: dict, scenario: str = "base", month: int = 0,
            usage: float = 1.0, answer_model: str | None = None, answer_length: float = 1.0,
            price_factor: float = 1.0) -> tuple[dict, Workload]:
    """Returns ({driver: US$ per month}, workload)."""
    model = answer_model or design.answer_model
    w = compute(demand, design, m, scenario, month, usage, model, answer_length)
    raw = {k: v.value for k, v in p.items()}                 # free amounts and shares do not scale
    price = {k: v * price_factor for k, v in raw.items()}
    days = demand.days_per_month
    asked = w.questions_per_month * (1 - design.get("cache_hit_share", scenario))   # a cache hit calls no model

    # Model tokens. Answers: the design's model(s); summaries: chat-small; embeddings: embed-small.
    answer = 0.0
    if model in ("small", "routed"):
        answer += asked * (m["answer_small_tokens_in"].value * price["chat_small_input"]
                           + m["answer_small_tokens_out"].value * answer_length * price["chat_small_output"]) / 1e6
    if model in ("strong", "routed"):
        share = 1.0 if model == "strong" else m["routed_escalation_share"].value
        answer += asked * share * (m["answer_strong_tokens_in"].value * price["chat_strong_input"]
                                   + m["answer_strong_tokens_out"].value * answer_length * price["chat_strong_output"]) / 1e6
    q_embed = _per_million(w.questions_per_month * m["question_embed_tokens"].value, price["embed_small_input"])
    ingest = _per_million(w.words_changed_per_month * m["ingest_embed_tokens_per_word"].value, price["embed_small_input"])
    summaries = (_per_million(w.document_changes_per_month * m["summary_tokens_in_fixed"].value
                              + w.words_changed_per_month * m["summary_tokens_in_per_word"].value, price["chat_small_input"])
                 + _per_million(w.document_changes_per_month * m["summary_small_tokens_out"].value, price["chat_small_output"]))
    retries = (answer + q_embed + ingest + summaries) * design.get("retry_share", scenario)

    # Database: a server that runs every hour, the storage you provision, backups over the free amount.
    server = price[design.database_price] * HOURS_PER_MONTH
    used_gb = sum(w.storage_gb.values()) - w.storage_gb["files"]
    provisioned = max(design.database_storage_gb, used_gb)
    db_storage = provisioned * price["pg_storage_gb_month"]
    backup_gb = used_gb * design.get("backup_size_factor", scenario)
    backups = _after_free(backup_gb, provisioned * raw["pg_backup_free_share"]) * price["pg_backup_gb_month"]

    files = w.storage_gb["files"] * price["blob_hot_gb_month"] + \
        w.document_changes_per_month * 2 / 10_000 * price["blob_write_10k"]

    # Compute: API replicas run all month (busy hours at the active price, the rest at the idle price);
    # the worker runs only while it ingests (scale to zero). The free grant is shared by both.
    busy = design.get("busy_hours_per_day", scenario) * 3600 * days * design.api_replicas
    idle = (24 * 3600 * days * design.api_replicas) - busy
    api_vcpu_active = busy * design.api_vcpu
    api_mem = (busy + idle) * design.api_memory_gib
    worker_vcpu = w.worker_seconds_per_month * design.worker_vcpu
    worker_mem = w.worker_seconds_per_month * design.worker_memory_gib
    free_vcpu, free_mem = raw["aca_free_vcpu_seconds"], raw["aca_free_gib_seconds"]
    vcpu_paid = _after_free(api_vcpu_active + worker_vcpu, free_vcpu)
    mem_paid = _after_free(api_mem + worker_mem, free_mem)
    vcpu_share_api = api_vcpu_active / max(api_vcpu_active + worker_vcpu, 1e-9)
    mem_share_api = api_mem / max(api_mem + worker_mem, 1e-9)
    compute_api = (vcpu_paid * vcpu_share_api * price["aca_vcpu_active_second"]
                   + idle * design.api_vcpu * price["aca_vcpu_idle_second"]
                   + mem_paid * mem_share_api * price["aca_memory_gib_second"])
    compute_worker = (vcpu_paid * (1 - vcpu_share_api) * price["aca_vcpu_active_second"]
                      + mem_paid * (1 - mem_share_api) * price["aca_memory_gib_second"])
    requests = _after_free(w.questions_per_month, raw["aca_free_requests"]) / 1e6 * price["aca_requests_million"]

    log_gb = w.questions_per_month * design.get("log_kb_per_question", scenario) / 1e6
    logs = _after_free(log_gb, raw["log_free_gb_month"]) * price["log_ingestion_gb"]
    out_gb = w.questions_per_month * (m["answer_response_bytes"].value + design.get("response_overhead_bytes", scenario)) / 1e9
    network = _after_free(out_gb, raw["egress_free_gb_month"]) * price["egress_internet_gb"]

    costs = dict(zip(DRIVERS, (answer, q_embed, ingest, summaries, retries, server, db_storage, backups, files,
                               compute_api, compute_worker, requests, logs, network), strict=True))
    return costs, w


def cost_table(costs: dict, title: str) -> str:
    total = sum(costs.values())
    lines = [title, f"  {'Driver':<36} {'US$ per month':>14} {'share':>7}"]
    for name, usd in sorted(costs.items(), key=lambda kv: -kv[1]):
        share = usd / total if total else 0
        lines.append(f"  {name:<36} {usd:>14,.2f} {share:>7.1%}")
    lines.append(f"  {'Total':<36} {total:>14,.2f}")
    top = max(costs, key=costs.get)
    lines.append(f"Biggest driver: {top} ({costs[top] / total:.0%} of the total)")
    return "\n".join(lines)
