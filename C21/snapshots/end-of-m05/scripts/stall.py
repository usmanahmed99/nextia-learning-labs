"""Does the server still answer while it waits for the AI provider?

    python -m scripts.stall [--tickets 8] [--concurrency 4] [--url http://127.0.0.1:8000]

It sends new tickets and, at the same time, asks GET /health every 0.1 s. /health does no
work at all, so it should answer in a few milliseconds. If it waits seconds, something in
the server blocks every request: compare INTAKE_MODE=async and INTAKE_MODE=blocking.
"""

import argparse
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from scripts.breakdown import tickets
from ticket_api.config import load_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tickets", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    load_env()
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    done = threading.Event()
    health_ms: list[float] = []

    def probe() -> None:
        with httpx.Client(base_url=args.url, timeout=60) as c:
            while not done.is_set():
                started = time.perf_counter()
                c.get("/health")
                health_ms.append((time.perf_counter() - started) * 1000)
                time.sleep(0.1)

    prober = threading.Thread(target=probe)
    prober.start()
    started = time.perf_counter()
    with httpx.Client(base_url=args.url, headers=headers, timeout=120) as client:
        with ThreadPoolExecutor(args.concurrency) as pool:
            statuses = list(
                pool.map(
                    lambda t: client.post("/v1/tickets", json=t).status_code, tickets(args.tickets)
                )
            )
    seconds = time.perf_counter() - started
    done.set()
    prober.join()
    print(
        f"{args.tickets} tickets, {args.concurrency} at a time: {seconds:.1f} s, "
        f"status codes {sorted(set(statuses))}"
    )
    print(
        f"GET /health during that time: {len(health_ms)} answers, median "
        f"{statistics.median(health_ms):.1f} ms, slowest {max(health_ms):.1f} ms"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
