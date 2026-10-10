"""Constructed on purpose: one message delivered twice. Does the work happen twice?

    python -m scripts.duplicate_demo

Part 1, the repeated request: the same new ticket is sent twice with the same
Idempotency-Key (as a client does when it did not get the first answer).
Part 2, the repeated delivery: a worker does all the steps of a job and stops before it
marks the job finished (a crash, simulated); its lease ends; a second worker takes the
same job. Both parts count the tickets, the jobs, the AI results and the provider calls.
It runs everything in this process, on your .env database, with the simulated provider.
"""

import asyncio
import sys
import uuid
from dataclasses import replace

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from scripts.breakdown import provider_stats
from ticket_api.config import load_settings
from ticket_api.main import create_app
from ticket_api.worker import Worker, make_worker

TICKET = {
    "customer_id": "C-0022",
    "subject": "Charged twice for order LK-182074",
    "body": "My card was charged two times for the same order.",
}


LEASE = 4.0  # seconds; longer than the work of one job (about 2.2 s)


class Crash(Exception):
    """The simulated crash: the worker stops after its work, before it finishes the job."""


async def crash_before_finish(worker: Worker) -> None:
    def no_finish(job, state, error=None):
        raise Crash()

    worker._finish = no_finish  # constructed: replace the last step with a crash
    await worker.run_once()  # take the job, then stop: nothing else after the crash
    await asyncio.gather(*worker.in_flight, return_exceptions=True)


def counts(conn, ticket_id: str) -> str:
    n = conn.execute(
        "SELECT (SELECT count(*) FROM tickets WHERE ticket_id = %(t)s) AS tickets,"
        " (SELECT count(*) FROM jobs WHERE ticket_id = %(t)s) AS jobs,"
        " (SELECT count(*) FROM ai_runs WHERE ticket_id = %(t)s) AS ai_results",
        {"t": ticket_id},
    ).fetchone()
    return f"tickets {n['tickets']}, jobs {n['jobs']}, AI results {n['ai_results']}"


def provider_calls(url: str) -> int:
    s = provider_stats(url) or {"calls": {}}
    return sum(n for task in s["calls"].values() for code, n in task.items() if code == "200")


def main() -> int:
    settings = replace(
        load_settings(), job_lease_seconds=1.0, worker_concurrency=1, rate_limit_per_minute=0
    )
    key = f"demo-{uuid.uuid4().hex[:12]}"
    ticket = {**TICKET, "body": f"{TICKET['body']} (demo {key[5:]})"}  # a new text: no cache hit
    with TestClient(create_app(settings)) as api:
        first = api.post("/v1/tickets", json=ticket, headers={"Idempotency-Key": key})
        again = api.post("/v1/tickets", json=ticket, headers={"Idempotency-Key": key})
    a, b = first.json(), again.json()
    print("Part 1: the same request twice, with the same Idempotency-Key")
    print(f"  first:  {first.status_code} ticket {a['ticket_id']} job {a['job_id']}")
    print(
        f"  second: {again.status_code} ticket {b['ticket_id']} job {b['job_id']} "
        f"(Idempotent-Replayed: {again.headers.get('Idempotent-Replayed')})"
    )
    with psycopg.connect(settings.database_url, autocommit=True, row_factory=dict_row) as conn:
        print(f"  in the database: {counts(conn, a['ticket_id'])}")
        print("Part 2: the same job delivered twice (a simulated crash)")
        before = provider_calls(settings.provider_url)

        async def deliver_twice() -> None:
            for name, crash in (("worker-1", True), ("worker-2", False)):
                w = make_worker(settings, name=name)
                w.db.open()
                try:
                    if crash:
                        await crash_before_finish(w)
                        await asyncio.sleep(LEASE + 0.2)  # the lease ends
                    else:
                        await w.drain()
                finally:
                    w.db.close()
                    await w.provider.aclose()
                    if w.cache is not None:
                        await w.cache.close()
                job = conn.execute(
                    "SELECT state, attempts, locked_by FROM jobs WHERE job_id = %s", (a["job_id"],)
                ).fetchone()
                print(
                    f"  after {name}{' (crashed before finishing)' if crash else ''}: job "
                    f"{job['state']}, attempt {job['attempts']}; {counts(conn, a['ticket_id'])}"
                )

        asyncio.run(deliver_twice())
        after = provider_calls(settings.provider_url)
        print(
            f"  provider calls for this job: {after - before} (3 steps: classify, draft_reply, "
            "embed)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
