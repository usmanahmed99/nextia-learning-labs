"""The answers and the timing of the simulated provider (no network, no clock: easy to test)."""

import hashlib
import json
import math
import random
import re
import time
from pathlib import Path

from ticket_api.classifier import KeywordClassifier11

CALIBRATION = json.loads((Path(__file__).parent / "calibration.json").read_text(encoding="utf-8"))
DIMENSIONS = 384
_classifier = KeywordClassifier11()
_words = re.compile(r"[a-z0-9]+")


def sample_latency_ms(task: str, rng: random.Random) -> float:
    """A time in ms drawn from the recorded times of this task (the empirical distribution).
    No answer to a question was recorded: answers take the times of the recorded replies."""
    times = CALIBRATION["latency_ms"]["draft_reply" if task == "answer" else task]
    x = rng.random() * (len(times) - 1)
    i = int(x)
    return times[i] + (times[min(i + 1, len(times) - 1)] - times[i]) * (x - i)


def tokens_in(task: str, text: str) -> int:
    a, b = CALIBRATION["tokens_in"]["draft_reply" if task == "answer" else task]
    return max(1, round(a + b * len(text)))


def _user_text(body: dict) -> str:
    for m in body.get("messages", []):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


def chat_task(body: dict) -> str:
    """classify, draft_reply or answer, from the request (classify asks for JSON; a question
    starts with "Question:")."""
    if body.get("response_format"):
        return "classify"
    return "answer" if _user_text(body).startswith("Question:") else "draft_reply"


def _answer_text(text: str) -> str:
    """A short answer made from the context: the first document's title and, for a customer,
    their latest ticket. (A real model writes better answers; the shape is what matters.)"""
    lines = text.splitlines()
    docs = [x[3:].split("]", 1)[0] for x in lines if x.startswith("- [")]
    tickets_at = lines.index("The customer's latest tickets:") if (
        "The customer's latest tickets:" in lines) else None
    out = []
    if docs:
        out.append(f'The document "{docs[0]}" has the details.')
    else:
        out.append("A person on the help desk will help you with this.")
    if tickets_at is not None and tickets_at + 1 < len(lines):
        ticket = lines[tickets_at + 1][2:]
        out.append(f"Your latest ticket is {ticket}.")
    return " ".join(out)


def _subject_and_body(text: str) -> tuple[str, str]:
    first, _, rest = text.partition("\n")
    return first.removeprefix("Subject: ").strip(), rest.strip()


def _key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def chat_answer(body: dict, model: str) -> dict:
    task = chat_task(body)
    text = _user_text(body)
    recorded = CALIBRATION["answers"].get(f"{task}:{_key(text)}")
    if task == "classify":
        if recorded is not None:
            content = recorded
        else:
            p = _classifier.predict(text)
            content = json.dumps(
                {"team": p.category, "priority": p.priority}, separators=(",", ":")
            )
        out = CALIBRATION["tokens_out"]["classify"]
    elif task == "answer":
        content = _answer_text(text)
        out = max(1, round(len(content) / CALIBRATION["chars_per_token_out"]))
    else:
        if recorded is not None:
            content = recorded
        else:
            subject, _ = _subject_and_body(text)
            content = (
                f'Thank you for your message about "{subject}". A person on our help desk will '
                "look at it and reply to you soon. If you have an order number, please send it."
            )
        out = max(1, round(len(content) / CALIBRATION["chars_per_token_out"]))
    prompt = tokens_in(task, text)
    return {
        "id": "chatcmpl-sim-" + _key(text + str(time.time_ns())),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": f"{model} (simulated)",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": prompt, "completion_tokens": out, "total_tokens": prompt + out},
    }


def embedding(text: str) -> list[float]:
    """A vector from the words of the text (feature hashing): texts that share words get
    similar vectors. It has no meaning beyond that; it is not a real embedding model."""
    v = [0.0] * DIMENSIONS
    for w in _words.findall(text.lower()):
        h = int.from_bytes(hashlib.sha256(w.encode()).digest()[:8], "big")
        v[h % DIMENSIONS] += 1.0 if (h >> 32) & 1 else -1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / norm, 6) for x in v]


def embed_answer(body: dict, model: str) -> dict:
    text = body.get("input", "")
    if isinstance(text, list):
        text = " ".join(map(str, text))
    dims = int(body.get("dimensions") or DIMENSIONS)
    vector = embedding(str(text))[:dims] if dims <= DIMENSIONS else embedding(str(text))
    prompt = tokens_in("embed", str(text))
    return {
        "object": "list",
        "data": [{"object": "embedding", "index": 0, "embedding": vector}],
        "model": f"{model} (simulated)",
        "usage": {"prompt_tokens": prompt, "total_tokens": prompt},
    }


def request_tokens(path: str, body: dict) -> int:
    """The tokens that the quota counts for a request (prompt + the most it may write)."""
    if path == "embeddings":
        text = body.get("input", "")
        return tokens_in("embed", text if isinstance(text, str) else " ".join(map(str, text)))
    task = chat_task(body)
    return tokens_in(task, _user_text(body)) + int(body.get("max_completion_tokens") or 0)
