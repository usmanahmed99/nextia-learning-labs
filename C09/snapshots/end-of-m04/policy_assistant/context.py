"""Assemble the context: choose the passages that go into the prompt, within a token budget.

1. Keep the search order (the best passage first).
2. Remove near-duplicates: two passages whose words are almost the same (Jaccard similarity of their
   word sets >= 0.9, title line left out), for example the same paragraph in the PW-2200 and PW-2400
   guides. The first (better-ranked) one stays. Two versions of the same document are NOT merged:
   their differences (30 days or 45 days) are the point, and the date filter decides between them.
3. Stop before the budget is used up. Tokens are estimated as characters / 4 (good enough for a
   budget; the provider reports the real count).
Every passage keeps its chunk ID and its source, so that the answer can cite it.
"""

import math
import re
from dataclasses import dataclass, field

BUDGET = 1500       # estimated tokens of passages per question
SIMILAR = 0.9


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


def word_set(text: str) -> set[str]:
    body = text.split("\n", 1)[1] if "\n" in text else text
    return set(re.findall(r"\w+", body.lower()))


def jaccard(a: str, b: str) -> float:
    wa, wb = word_set(a), word_set(b)
    return len(wa & wb) / len(wa | wb) if wa | wb else 1.0


def format_passage(chunk) -> str:
    dates = f"in force from {chunk.effective_from}" + (f" to {chunk.effective_to}" if chunk.effective_to else ", no end date")
    return (f"[{chunk.chunk_id}] {chunk.title} | {chunk.doc_type}, version {chunk.version}, {dates} | "
            f"section: {chunk.section or '-'}\n{chunk.text}")


@dataclass
class Context:
    chunks: list = field(default_factory=list)
    dropped: list = field(default_factory=list)     # (chunk_id, reason)
    tokens: int = 0

    @property
    def ids(self) -> list[str]:
        return [c.chunk_id for c in self.chunks]

    def text(self) -> str:
        return "\n\n".join(format_passage(c) for c in self.chunks)


def assemble(chunks: list, budget: int = BUDGET) -> Context:
    ctx = Context()
    for chunk in chunks:
        twin = next((c for c in ctx.chunks if c.doc_id != chunk.doc_id and jaccard(c.text, chunk.text) >= SIMILAR), None)
        if twin is not None:
            ctx.dropped.append((chunk.chunk_id, f"near-duplicate of {twin.chunk_id}"))
            continue
        cost = estimate_tokens(format_passage(chunk))
        if ctx.tokens + cost > budget:
            ctx.dropped.append((chunk.chunk_id, "over budget"))
            continue
        ctx.chunks.append(chunk)
        ctx.tokens += cost
    return ctx
