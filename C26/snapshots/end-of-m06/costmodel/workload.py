"""Workload arithmetic: from demand to the numbers that cost money (Module 3, lesson 1).

The three rules of this lesson:
- volume:      questions per month = questions per day x days per month
- concurrency: requests in flight = arrival rate x time in the system (Little's law)
- growth:      storage after n months = storage now + changes per month x n
Every function returns plain numbers, so a test (or a spreadsheet) can check each step.
"""

from dataclasses import dataclass

from .demand import Demand, active, questions_per_day
from .design import Design

MODELS = ("chat-small", "chat-strong", "embed-small")


@dataclass(frozen=True)
class Workload:
    scenario: str
    month: int
    tenants: int
    questions_per_month: float
    questions_by_tenant: dict          # tenant name -> questions per month
    documents: float
    document_changes_per_month: float
    words_changed_per_month: float
    peak_hour_questions: float
    peak_per_second: float             # in the busiest minute
    seconds_in_system: float           # one question, from arrival to answer (median)
    in_flight_at_peak: float           # concurrency = arrival rate x time in system
    model_calls_peak_minute: float     # chat calls in the busiest minute
    tokens: dict                       # model -> {"in": tokens, "out": tokens} per month
    storage_gb: dict                   # what -> GB now
    storage_growth_gb_per_month: float
    worker_seconds_per_month: float


def answer_tokens(m: dict, model: str, factor_out: float = 1.0) -> dict:
    """Tokens of one answer for each chat model, for the design's answer model."""
    small = {"in": m["answer_small_tokens_in"].value, "out": m["answer_small_tokens_out"].value * factor_out}
    strong = {"in": m["answer_strong_tokens_in"].value, "out": m["answer_strong_tokens_out"].value * factor_out}
    if model == "small":
        return {"chat-small": small}
    if model == "strong":
        return {"chat-strong": strong}
    share = m["routed_escalation_share"].value   # every question goes to chat-small; some again to chat-strong
    return {"chat-small": small, "chat-strong": {k: v * share for k, v in strong.items()}}


def answer_seconds(m: dict, model: str) -> float:
    key = {"small": "answer_small_p50_s", "strong": "answer_strong_p50_s", "routed": "routed_p50_s"}[model]
    return m["question_embed_p50_s"].value + m["retrieval_rerank_s"].value + m[key].value


def compute(demand: Demand, design: Design, m: dict, scenario: str = "base", month: int = 0,
            usage: float = 1.0, answer_model: str | None = None, answer_length: float = 1.0) -> Workload:
    model = answer_model or design.answer_model
    tenants = active(demand, month)
    days = demand.days_per_month
    by_tenant = {t.name: questions_per_day(t, scenario, month, usage) * days for t in tenants}
    questions = sum(by_tenant.values())
    asked = questions * (1 - design.get("cache_hit_share", scenario))   # a cache hit calls no model
    documents = sum(t.get("documents", scenario) for t in tenants)
    changes = sum(t.get("document_changes_per_month", scenario) for t in tenants)
    words_changed = sum(t.get("document_changes_per_month", scenario) * t.get("words_per_document", scenario)
                        for t in tenants)
    words_all = sum(t.get("documents", scenario) * t.get("words_per_document", scenario) for t in tenants)

    peak_hour = questions / days * demand.setting("peak_hour_share", scenario)
    peak_per_second = peak_hour / 3600 * demand.setting("peak_minute_factor", scenario)
    seconds = answer_seconds(m, model)
    per_answer = answer_tokens(m, model, answer_length)
    chat_calls_per_question = len(per_answer) if model != "routed" else 1 + m["routed_escalation_share"].value

    tokens = {k: {"in": 0.0, "out": 0.0} for k in MODELS}
    for name, t in per_answer.items():
        tokens[name]["in"] += asked * t["in"]
        tokens[name]["out"] += asked * t["out"]
    tokens["embed-small"]["in"] += questions * m["question_embed_tokens"].value      # every question is embedded
    tokens["embed-small"]["in"] += words_changed * m["ingest_embed_tokens_per_word"].value
    tokens["chat-small"]["in"] += (changes * m["summary_tokens_in_fixed"].value
                                   + words_changed * m["summary_tokens_in_per_word"].value)
    tokens["chat-small"]["out"] += changes * m["summary_small_tokens_out"].value

    gb = 1e9
    versions = design.get("versions_kept", scenario)
    storage = {
        "files": documents * versions * m["document_file_bytes"].value / gb,
        "chunks and vectors": (words_all / 1000 * m["chunks_per_1000_words"].value * m["vector_row_bytes"].value
                               + words_all * m["chunk_text_bytes_per_word"].value) / gb,
        "answers and logs in the database": questions * m["answer_row_bytes"].value / gb,
    }
    growth = (changes * m["document_file_bytes"].value + questions * m["answer_row_bytes"].value) / gb
    worker = changes * (m["ingest_embed_s_per_document"].value + m["summary_small_p50_s"].value)
    return Workload(scenario, month, len(tenants), questions, by_tenant, documents, changes, words_changed,
                    peak_hour, peak_per_second, seconds, peak_per_second * seconds,
                    peak_per_second * 60 * chat_calls_per_question * (1 - design.get("cache_hit_share", scenario)),
                    tokens, storage, growth, worker)


def explain(w: Workload, m: dict) -> str:
    """The workload arithmetic with every step visible (python -m costmodel workload)."""
    tok = w.tokens
    lines = [
        f"Workload, scenario {w.scenario}, month {w.month} ({w.tenants} tenants)",
        f"  questions per month       {w.questions_per_month:>14,.0f}",
        f"  busiest hour              {w.peak_hour_questions:>14,.1f} questions",
        f"  busiest minute            {w.peak_per_second:>14,.3f} questions per second",
        f"  time in the system        {w.seconds_in_system:>14,.2f} s (embed the question + search + answer, medians)",
        f"  in flight at the peak     {w.in_flight_at_peak:>14,.2f} = {w.peak_per_second:.3f}/s x {w.seconds_in_system:.2f} s",
        f"  chat calls, busiest min.  {w.model_calls_peak_minute:>14,.1f} (provider quota: "
        f"{m['provider_quota_requests_per_minute'].value:,.0f} per minute)",
        f"  documents                 {w.documents:>14,.0f} ({w.document_changes_per_month:,.0f} changed per month)",
        "  tokens per month          " + ", ".join(
            f"{k} {v['in'] / 1e6:,.2f}M in / {v['out'] / 1e6:,.2f}M out" for k, v in tok.items() if v["in"] or v["out"]),
        "  storage now               " + ", ".join(f"{k} {v * 1000:,.1f} MB" for k, v in w.storage_gb.items()),
        f"  storage growth            {w.storage_growth_gb_per_month * 1000:>14,.1f} MB per month",
        f"  ingestion worker          {w.worker_seconds_per_month:>14,.0f} s busy per month",
    ]
    return "\n".join(lines)
