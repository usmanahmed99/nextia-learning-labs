"""One log line per model call: tokens, time, cost, request ID. No ticket text, no keys."""

import json
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import redact
from .providers import Completion

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "usage.jsonl"

# US dollars per million tokens (input, output). Output includes reasoning tokens.
# Azure AI Foundry, Global Standard deployments, prices checked on 2026-10-08. Check the current price page.
PRICES_CHECKED = "2026-10-08"
PRICES = {
    "chat-small": (0.10, 0.50),   # gpt-6-luna 2026-09-22
    "chat-strong": (2.00, 10.00),  # gpt-6.1-sol 2026-09-29
    "gemma3:4b": (0.0, 0.0),       # local model through Ollama: no price per token (your own computer)
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """None when the model is not in the price table: unknown cost is not zero cost."""
    if model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


@dataclass
class Budget:
    max_tokens_per_ticket: int = 8000
    max_cost_per_ticket_usd: float = 0.02


class UsageLog:
    def __init__(self, path: Path = LOG_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, completion: Completion, model: str, ticket_id: str, prompt: str, status: str = "ok",
               note: str = "") -> dict:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "request_id": completion.request_id,
            "model": model,
            "prompt": prompt,
            "ticket_id": ticket_id,
            "input_tokens": completion.input_tokens,
            "output_tokens": completion.output_tokens,
            "reasoning_tokens": completion.reasoning_tokens,
            "latency_s": completion.latency_s,
            "cost_usd": cost_usd(model, completion.input_tokens, completion.output_tokens),
            "prices_checked": PRICES_CHECKED,
            "finish_reason": completion.finish_reason,
            "status": status,
            "note": redact(note),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return entry

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]


def summarise(entries: list[dict]) -> dict:
    if not entries:
        return {"calls": 0}
    latencies = sorted(e["latency_s"] for e in entries)
    costs = [e["cost_usd"] for e in entries]
    return {
        "calls": len(entries),
        "input_tokens": sum(e["input_tokens"] for e in entries),
        "output_tokens": sum(e["output_tokens"] for e in entries),
        "latency_median_s": round(statistics.median(latencies), 2),
        "latency_p95_s": round(latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))], 2),
        "cost_usd": None if None in costs else round(sum(costs), 6),
    }


def over_budget(ticket_entries: list[dict], budget: Budget) -> list[str]:
    tokens = sum(e["input_tokens"] + e["output_tokens"] for e in ticket_entries)
    cost = sum(e["cost_usd"] or 0 for e in ticket_entries)
    reasons = []
    if tokens > budget.max_tokens_per_ticket:
        reasons.append(f"{tokens} tokens > {budget.max_tokens_per_ticket}")
    if cost > budget.max_cost_per_ticket_usd:
        reasons.append(f"US${cost:.4f} > US${budget.max_cost_per_ticket_usd}")
    return reasons
