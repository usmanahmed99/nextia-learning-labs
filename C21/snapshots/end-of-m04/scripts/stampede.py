"""Many requests for the same answer at the same moment, when it is not in the cache yet.

    python -m scripts.stampede [--requests 20] [--url http://127.0.0.1:8000]

It asks one new question (never asked before, so the cache has no answer) from 20 requests
at once, and counts what the cache did (X-Cache) and how many calls reached the provider.
Run it with CACHE_STAMPEDE_GUARD=true (the default) and false in the API's settings.
"""

import argparse
import os
import sys
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx

from scripts.breakdown import provider_stats
from ticket_api.config import load_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requests", type=int, default=20)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    load_env()
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    provider_url = os.environ.get("PROVIDER_URL", "http://127.0.0.1:8300/v1")
    question = {"question": f"How do I track my parcel? (question {uuid.uuid4().hex[:6]})"}
    before = provider_stats(provider_url)
    started = time.perf_counter()
    with httpx.Client(base_url=args.url, headers=headers, timeout=60) as client:
        with ThreadPoolExecutor(args.requests) as pool:
            rs = list(
                pool.map(lambda _: client.post("/v1/answers", json=question), range(args.requests))
            )
    seconds = time.perf_counter() - started
    after = provider_stats(provider_url)
    cache = Counter(r.headers.get("X-Cache", "?") for r in rs)
    print(
        f"{args.requests} requests for the same new question: {seconds:.2f} s, "
        f"status codes {dict(Counter(r.status_code for r in rs))}"
    )
    print(f"Cache: {dict(sorted(cache.items()))}")
    if before and after:
        n = after["calls"].get("answer", {}).get("200", 0) - before["calls"].get("answer", {}).get(
            "200", 0
        )
        print(f"Calls that reached the provider: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
