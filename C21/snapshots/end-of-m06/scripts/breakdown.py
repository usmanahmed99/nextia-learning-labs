"""Where does a new ticket's time go? Send tickets and add up their Server-Timing parts.

    python -m scripts.breakdown [--tickets 20] [--concurrency 1] [--url http://127.0.0.1:8000]

Run the API (fastapi dev) and the simulated provider (python -m simulator) first. Each
response says how long each part took (db, classify, draft_reply, embed). "other" is the
rest of the request: the web framework, JSON, the network between this script and the API.
It also prints what the provider counted (python -m simulator has /admin/stats).
"""

import argparse
import csv
import os
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ticket_api.config import load_env
from ticket_api.timing import parse

DATA = Path(__file__).resolve().parent.parent / "data" / "small" / "tickets.csv"


def tickets(n: int) -> list[dict]:
    rows = list(csv.DictReader(open(DATA, encoding="utf-8")))
    rng = random.Random(21)
    return [
        {"customer_id": r["customer_id"], "subject": r["subject"], "body": r["body"]}
        for r in rng.sample(rows, n)
    ]


def run(url: str, n: int, concurrency: int, headers: dict) -> list[dict]:
    with httpx.Client(base_url=url, headers=headers, timeout=120) as client:

        def one(t: dict) -> dict:
            started = time.perf_counter()
            r = client.post("/v1/tickets", json=t)
            total = (time.perf_counter() - started) * 1000
            return {
                "status": r.status_code,
                "total": total,
                "parts": parse(r.headers.get("server-timing", "")),
            }

        with ThreadPoolExecutor(concurrency) as pool:
            return list(pool.map(one, tickets(n)))


def provider_stats(url: str) -> dict | None:
    try:
        return httpx.get(url.rsplit("/v1", 1)[0] + "/admin/stats", timeout=2).json()
    except (httpx.HTTPError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickets", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    load_env()
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    provider_url = os.environ.get("PROVIDER_URL", "http://127.0.0.1:8300/v1")
    before = provider_stats(provider_url)
    results = run(args.url, args.tickets, args.concurrency, headers)
    after = provider_stats(provider_url)
    statuses: dict[int, int] = {}
    for r in results:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
    ok = [r for r in results if r["status"] in (201, 202)]
    print(f"{len(results)} tickets, {args.concurrency} at a time: status codes {statuses}")
    if not ok:
        return 1
    total = statistics.median(r["total"] for r in ok)
    names = [
        n for n in ("db", "classify", "draft_reply", "embed") if any(n in r["parts"] for r in ok)
    ]
    medians = {n: statistics.median(r["parts"].get(n, 0.0) for r in ok) for n in names}
    medians["other"] = statistics.median(r["total"] - sum(r["parts"].values()) for r in ok)
    print(f"{'part':<12} {'median ms':>10} {'share':>7}")
    for n, ms in medians.items():
        print(f"{n:<12} {ms:>10.1f} {ms / total:>7.0%}")
    print(f"{'total':<12} {total:>10.1f}")
    if before and after:
        calls = lambda s: {(t, c): n for t, d in s["calls"].items() for c, n in d.items()}  # noqa: E731
        b, a = calls(before), calls(after)
        refused = sum(n - b.get(k, 0) for k, n in a.items() if k[1] == "429")
        print(
            f"Provider ({'simulated' if after.get('simulated') else 'real'}): "
            f"{sum(n - b.get(k, 0) for k, n in a.items())} calls, {refused} refused with 429, "
            f"at most {after['max_in_flight']} at the same time"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
