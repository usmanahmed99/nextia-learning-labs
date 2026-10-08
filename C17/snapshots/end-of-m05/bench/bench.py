"""Send tickets to a running service and measure how long each answer takes.

    python bench/bench.py http://127.0.0.1:8000 --requests 1000 --concurrency 4

The workload is fixed, so two runs can be compared: the July tickets from
data/july_tickets.csv, in file order, one ticket per request. The first
--warmup requests are sent but not measured. Prints p50, p95, p99 and the
throughput, and adds one line to bench/results.jsonl with the settings.
"""

import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

FEATURES = ["channel", "team", "segment", "region", "priority", "order_value", "word_count",
            "customer_tenure_days", "prior_tickets_90d", "created_hour", "prior_escalations_90d"]
INTS = ["priority", "word_count", "customer_tenure_days", "prior_tickets_90d", "created_hour", "prior_escalations_90d"]


def load_tickets(path: Path) -> list[bytes]:
    df = pd.read_csv(path, keep_default_na=False, na_values=[""], dtype={c: "Int64" for c in INTS})
    bodies = []
    for row in df[["ticket_id"] + FEATURES].to_dict("records"):
        ticket = {k: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for k, v in row.items()}
        bodies.append(json.dumps(ticket).encode())
    return bodies


def percentile(values: list[float], p: float) -> float:
    return statistics.quantiles(values, n=100, method="inclusive")[p - 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=50)
    parser.add_argument("--label", default="", help="a name for this configuration, for the results file")
    parser.add_argument("--tickets", type=Path, default=Path("data/july_tickets.csv"))
    args = parser.parse_args()

    bodies = load_tickets(args.tickets)
    headers = {"Content-Type": "application/json"}
    if os.environ.get("API_KEY"):
        headers["X-API-Key"] = os.environ["API_KEY"]

    def send(i: int) -> tuple[float, int]:
        request = urllib.request.Request(f"{args.url}/v1/score", data=bodies[i % len(bodies)], headers=headers)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except OSError:
            status = 0
        return (time.perf_counter() - started) * 1000, status

    for i in range(args.warmup):
        send(i)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(send, range(args.warmup, args.warmup + args.requests)))
    seconds = time.perf_counter() - started

    ms = [r[0] for r in results if r[1] == 200]
    errors = sum(1 for r in results if r[1] != 200)
    summary = {
        "label": args.label,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "requests": args.requests,
        "concurrency": args.concurrency,
        "errors": errors,
        "p50_ms": round(percentile(ms, 50), 1),
        "p95_ms": round(percentile(ms, 95), 1),
        "p99_ms": round(percentile(ms, 99), 1),
        "max_ms": round(max(ms), 1),
        "per_second": round(args.requests / seconds, 1),
    }
    print(f"{args.requests} requests, concurrency {args.concurrency}: p50 {summary['p50_ms']} ms, "
          f"p95 {summary['p95_ms']} ms, p99 {summary['p99_ms']} ms, max {summary['max_ms']} ms, "
          f"{summary['per_second']} requests/s, {errors} errors.")
    with open(Path(__file__).parent / "results.jsonl", "a", encoding="utf-8") as out:
        out.write(json.dumps(summary) + "\n")


if __name__ == "__main__":
    main()
