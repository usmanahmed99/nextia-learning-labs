"""A simulated provider outage: what the worker does with and without a circuit breaker.

    python -m scripts.outage_demo [--breaker on|off] [--jobs 30] [--outage 20]

Needs the simulated provider (python -m simulator) and the database of your .env. It
queues new tickets, turns the provider's outage mode on, runs a worker during the outage,
turns the outage off, and lets the worker finish. It prints the calls that reached the
provider during the outage, and the jobs' states at the end. (The outage is simulated.)
"""

import argparse
import asyncio
import sys
import time
from dataclasses import replace

import httpx
import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from scripts.breakdown import provider_stats
from ticket_api.config import load_settings
from ticket_api.main import create_app
from ticket_api.worker import make_worker


def calls(url: str) -> dict:
    s = provider_stats(url) or {"calls": {}}
    out: dict[str, int] = {}
    for task in s["calls"].values():
        for code, n in task.items():
            out[code] = out.get(code, 0) + n
    return out


def mode(url: str, name: str) -> None:
    httpx.post(url.rsplit("/v1", 1)[0] + "/admin/mode", json={"mode": name}, timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--breaker", choices=["on", "off"], default="on")
    parser.add_argument("--jobs", type=int, default=30)
    parser.add_argument("--outage", type=float, default=20.0, help="seconds")
    args = parser.parse_args(argv)
    s = load_settings()
    s = replace(
        s,
        rate_limit_per_minute=0,
        breaker_failures=s.breaker_failures if args.breaker == "on" else 0,
        retry_base_seconds=1.0,
        retry_cap_seconds=8.0,
        worker_drain_seconds=1.0,
    )
    url = s.provider_url
    with TestClient(create_app(s)) as api:
        for i in range(args.jobs):
            api.post(
                "/v1/tickets",
                json={
                    "customer_id": f"C-{i % 40 + 1:04d}",
                    "subject": f"Outage test {i}",
                    "body": "Where is it?",
                },
            )
    worker = make_worker(s, name=f"outage-demo-{args.breaker}")

    async def run() -> dict:
        worker.db.open()
        stop = asyncio.Event()
        runner = asyncio.create_task(worker.run_forever(stop))
        mode(url, "outage")
        before = calls(url)
        await asyncio.sleep(args.outage)
        during = calls(url)
        mode(url, "normal")
        print(f"Outage over after {args.outage:.0f} s (simulated).", flush=True)
        # Long enough for an open circuit to try again, and for the queue to empty.
        await asyncio.sleep(max(args.outage * 2, s.breaker_open_seconds + 15))
        stop.set()
        await runner
        worker.db.close()
        return {k: during.get(k, 0) - before.get(k, 0) for k in set(during) | set(before)}

    started = time.perf_counter()
    during = asyncio.run(run())
    with psycopg.connect(s.database_url, row_factory=dict_row) as conn:
        states = conn.execute(
            "SELECT state, count(*) AS n FROM jobs WHERE ticket_id IN (SELECT"
            " ticket_id FROM tickets WHERE subject LIKE 'Outage test %%')"
            " GROUP BY state ORDER BY state"
        ).fetchall()
    b = worker.provider.breaker
    print(f"Circuit breaker: {args.breaker}" + (f" (opened {b.opened_count} time(s))" if b else ""))
    print(
        f"Calls that reached the provider during the outage: {sum(during.values())} "
        f"(answered {dict(sorted(during.items()))})"
    )
    print(
        f"Jobs at the end ({time.perf_counter() - started:.0f} s): "
        + ", ".join(f"{r['state']} {r['n']}" for r in states)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
