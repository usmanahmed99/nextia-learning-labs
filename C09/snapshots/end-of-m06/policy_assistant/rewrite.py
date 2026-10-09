"""Query rewriting: ask a model to turn the agent's question into a better search query.

It can help (a French question becomes English words that match English documents; "two years without
buying" becomes "points expiry") and it can hurt (the model drops a date or a code, or answers the
question instead of searching). Measure it like any other change. The course's rewrites were recorded
with chat-small; the mock replays them.
"""

from .config import load_prompt

MAX_TOKENS = 1000


def build_request(question: str, model: str) -> dict:
    system, user = load_prompt("rewrite")
    return {"model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user.format(question=question)}],
            "max_completion_tokens": MAX_TOKENS}


def rewrite(question: str, provider, model: str = "chat-small") -> str:
    completion = provider.complete(build_request(question, model))
    text = (completion.text or "").strip().splitlines()
    return text[0].strip().strip('"') if text else question
