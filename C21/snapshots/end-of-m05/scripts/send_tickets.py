"""Send new tickets at a fixed arrival rate (an open workload), and count the answers.

    python -m scripts.send_tickets --rate 5 --seconds 30 [--url http://127.0.0.1:8000]

Unlike a load generator whose users wait for each answer, this sends a ticket every
1/rate seconds whatever happens (customers do not wait for each other). So when the
service is slow, work piles up: in the queue, or as errors. It prints the status codes and
the Retry-After values that the API sent back.
"""

import argparse
import asyncio
import os
import sys
import time
from collections import Counter

import httpx

from scripts.breakdown import tickets
from ticket_api.config import load_env


async def send(
    url: str, rate: float, seconds: float, headers: dict
) -> tuple[Counter, Counter, list]:
    statuses: Counter = Counter()
    retry_after: Counter = Counter()
    latencies: list[float] = []
    n = max(1, int(rate * seconds))
    pool = tickets(min(n, 200))
    limits = httpx.Limits(max_connections=200)
    async with httpx.AsyncClient(base_url=url, headers=headers, timeout=60, limits=limits) as c:

        async def one(i: int) -> None:
            started = time.perf_counter()
            try:
                r = await c.post("/v1/tickets", json=pool[i % len(pool)])
            except httpx.HTTPError as error:
                statuses[type(error).__name__] += 1
                return
            latencies.append((time.perf_counter() - started) * 1000)
            statuses[r.status_code] += 1
            if "retry-after" in r.headers:
                retry_after[r.headers["retry-after"]] += 1

        tasks = []
        t0 = time.perf_counter()
        for i in range(n):
            delay = t0 + i / rate - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(one(i)))
        await asyncio.gather(*tasks)
    return statuses, retry_after, latencies


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rate", type=float, default=5.0, help="tickets per second")
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    load_env()
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    started = time.perf_counter()
    statuses, retry_after, latencies = asyncio.run(send(args.url, args.rate, args.seconds, headers))
    latencies.sort()
    p95 = latencies[int(0.95 * (len(latencies) - 1))] if latencies else 0
    print(
        f"Sent {sum(statuses.values())} tickets at {args.rate:g} per second in "
        f"{time.perf_counter() - started:.1f} s: status codes {dict(sorted(statuses.items()))}"
    )
    if retry_after:
        print(f"Retry-After values: {dict(sorted(retry_after.items(), key=lambda x: int(x[0])))}")
    print(f"Answer time: median {latencies[len(latencies) // 2]:.0f} ms, p95 {p95:.0f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
