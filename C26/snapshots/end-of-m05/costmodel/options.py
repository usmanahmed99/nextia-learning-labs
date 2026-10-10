"""Options with measured trade-offs (Module 4): model routing, caching and batching.

Quality and time come from measured.toml (real runs on the same 67 questions); cost comes from
the cost model with the same workload, so the three designs are compared fairly: one workload,
one quality check, one price list.
"""

from .costs import monthly
from .units import units

DESIGN_KEYS = {"small": "answer_small", "strong": "answer_strong", "routed": "routed"}
LABELS = {"small": "chat-small only", "strong": "chat-strong only", "routed": "routed (small first)"}


def answer_cost_per_question(m: dict, p: dict, model: str) -> float:
    small = (m["answer_small_tokens_in"].value * p["chat_small_input"].value
             + m["answer_small_tokens_out"].value * p["chat_small_output"].value) / 1e6
    strong = (m["answer_strong_tokens_in"].value * p["chat_strong_input"].value
              + m["answer_strong_tokens_out"].value * p["chat_strong_output"].value) / 1e6
    return {"small": small, "strong": strong, "routed": small + m["routed_escalation_share"].value * strong}[model]


def routing_rows(demand, design, m, p, scenario="base") -> list[dict]:
    rows = []
    for model, key in DESIGN_KEYS.items():
        p50 = m[f"{key}_p50_s"].value
        p95 = m[f"{key}_p95_s"].value
        rows.append({
            "design": LABELS[model], "model": model,
            "correct_share": m[f"{key}_correct_share"].value,
            "usd_per_question": answer_cost_per_question(m, p, model),
            "p50_s": p50, "p95_s": p95,
            "monthly_total": units(demand, design, m, p, scenario, answer_model=model).total,
        })
    return rows


def routing_table(rows: list[dict]) -> str:
    lines = ["Model routing: the same 67 questions, the same search results (measured), base workload (cost model)",
             f"  {'design':<24} {'correct':>8} {'US$/question':>13} {'p50 s':>7} {'p95 s':>7} {'US$/month':>10}"]
    for r in rows:
        lines.append(f"  {r['design']:<24} {r['correct_share']:>8.1%} {r['usd_per_question']:>13.6f} "
                     f"{r['p50_s']:>7.2f} {r['p95_s']:>7.2f} {r['monthly_total']:>10,.2f}")
    best = max(rows, key=lambda r: (round(r["correct_share"], 2), -r["usd_per_question"]))
    lines.append(f"Cheapest design with the best measured quality: {best['design']}")
    return "\n".join(lines)


def caching_table(demand, design, m, p, scenario="base") -> str:
    """The hit share is an assumption; the time and cost saved per hit are measured."""
    miss = m["question_embed_p50_s"].value + m["retrieval_rerank_s"].value + m["answer_small_p50_s"].value
    hit = m["cache_hit_s"].value
    lines = ["Caching answers: the hit share is an ASSUMPTION; the time saved per hit is measured",
             f"  a miss takes {miss:.2f} s (embed + search + answer, medians); a hit takes {hit:.3f} s",
             f"  {'hit share':>10} {'US$/month':>10} {'saved':>8} {'median wait s':>14}"]
    for share in (0.0, 0.1, 0.3, 0.5):
        a = dict(design.assumptions)
        a["cache_hit_share"] = (share, share, share)
        d = design.__class__(**{**design.__dict__, "assumptions": a})
        total = sum(monthly(demand, d, m, p, scenario)[0].values())
        if share == 0.0:
            base = total
        wait = hit if share > 0.5 else miss   # the median question is a miss while hits are under half
        lines.append(f"  {share:>10.0%} {total:>10,.2f} {base - total:>8,.2f} {wait:>14.2f}")
    lines.append("  The median wait does not change until more than half of the questions are hits.")
    return "\n".join(lines)


def batching_table(m: dict, p: dict) -> str:
    one = m["embed_one_call_per_chunk_s_per_document"].value
    batch = m["embed_one_call_per_document_s"].value
    flex = p["chat_small_flex_input"].value / p["chat_small_input"].value
    return "\n".join([
        "Batching and delay (measured times; prices from the price list)",
        f"  embed a document chunk by chunk  {one:>6.2f} s    in one call  {batch:>6.2f} s   "
        f"({one / batch:.1f} times faster, the same tokens and the same cost)",
        f"  a summary can wait: the Flex price of chat-small is {flex:.0%} of the normal price "
        "(price list; not tested in this course)",
        f"  the provider's own prompt cache: {m['provider_cached_share_long_prompt'].value:.1%} of a long repeated "
        f"request was cached; {m['provider_cached_share_answer_prompt'].value:.0%} of a normal answer request",
    ])
