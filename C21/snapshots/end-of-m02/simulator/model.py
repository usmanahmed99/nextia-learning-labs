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
    """A time in ms drawn from the recorded times of this task (the empirical distribution)."""
    times = CALIBRATION["latency_ms"][task]
    x = rng.random() * (len(times) - 1)
    i = int(x)
    return times[i] + (times[min(i + 1, len(times) - 1)] - times[i]) * (x - i)


def tokens_in(task: str, text: str) -> int:
    a, b = CALIBRATION["tokens_in"][task]
    return max(1, round(a + b * len(text)))


def _user_text(body: dict) -> str:
    for m in body.get("messages", []):
        if m.get("role") == "user":
            return str(m.get("content", ""))
    return ""


def chat_task(body: dict) -> str:
    """classify or draft_reply, from the request (the classify request asks for JSON)."""
    return "classify" if body.get("response_format") else "draft_reply"


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
