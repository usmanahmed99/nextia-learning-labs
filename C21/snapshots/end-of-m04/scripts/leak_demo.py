"""Constructed on purpose: a cache key without the caller's identity serves one customer's
answer to another. Run it only on your own practice data.

    python -m scripts.leak_demo

It runs the API in this process (with your .env: the database, the cache, the simulated
provider), asks the same question as two customers, first with a WRONG key (the question
only), then with the project's key (with the identity scope). It deletes its keys after.
"""

import sys

from fastapi.testclient import TestClient

from ticket_api import answers
from ticket_api.config import load_settings
from ticket_api.main import create_app

QUESTION = {"question": "Where is my parcel and how do I track it?"}
CUSTOMERS = ("C-0003", "C-0022")


def wrong_key(scope: str, generation: int, question: str, versions: dict) -> str:
    """THE MISTAKE: the key has only the question. Do not copy this."""
    return "ta:demo-wrong-key:" + question


def ask(client: TestClient) -> list[tuple[str, dict]]:
    out = []
    for c in CUSTOMERS:
        r = client.post("/v1/answers", json=QUESTION, headers={"X-Customer-ID": c})
        out.append((r.headers.get("X-Cache", "?"), r.json()))
    return out


def show(title: str, results: list[tuple[str, dict]]) -> None:
    print(title)
    for c, (status, body) in zip(CUSTOMERS, results, strict=True):
        print(f"  {c} asks -> cache {status}: {body['answer']}")


def main() -> int:
    settings = load_settings()
    if not settings.cache_url:
        print("CACHE_URL is not set (see .env.example).", file=sys.stderr)
        return 1
    right_key = answers.answer_key
    with TestClient(create_app(settings)) as client:
        answers.answer_key = wrong_key
        try:
            show("With the WRONG key (the question only):", ask(client))
        finally:
            answers.answer_key = right_key
        show("With the project's key (identity scope in the key):", ask(client))
    import redis

    r = redis.Redis.from_url(settings.cache_url)
    r.delete("ta:demo-wrong-key:" + QUESTION["question"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
