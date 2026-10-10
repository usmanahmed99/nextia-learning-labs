"""Replace a worker while it works: a graceful stop (SIGTERM) and a kill (SIGKILL).

    python -m scripts.shutdown_demo [--jobs 12] [--stop-after 3]

Needs the simulated provider (python -m simulator) and the database of your .env. It queues
new tickets, starts a worker process (python -m ticket_api.worker), and stops it after a
few seconds: first with SIGTERM (the worker finishes or gives back its running jobs), then,
in a second round, with SIGKILL (constructed: the worker cannot do anything; its jobs stay
"running" until their lease ends). A new worker then finishes the queue. It prints, for
each round, the jobs' states, the attempts, and the AI results per ticket.
On Windows there is no SIGKILL: the second round uses terminate(), which stops the process
at once in the same way.
"""

import argparse
import os
import signal
import subprocess
import sys
import time

import psycopg
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from ticket_api.config import load_settings
from ticket_api.main import create_app

LEASE = 10  # seconds, for this demo


def queue_tickets(n: int, tag: str) -> None:
    from dataclasses import replace

    s = replace(load_settings(), rate_limit_per_minute=0)
    with TestClient(create_app(s)) as api:
        for i in range(n):
            api.post(
                "/v1/tickets",
                json={
                    "customer_id": f"C-{i % 40 + 1:04d}",
                    "subject": f"{tag} {i}",
                    "body": "Where is my order?",
                },
            )


def report(conn, tag: str) -> str:
    rows = conn.execute(
        "SELECT j.state, j.attempts, (SELECT count(*) FROM ai_runs a WHERE a.job_id = j.job_id)"
        " AS results FROM jobs j JOIN tickets t USING (ticket_id) WHERE t.subject LIKE %s",
        (f"{tag} %",),
    ).fetchall()
    states: dict[str, int] = {}
    for r in rows:
        states[r["state"]] = states.get(r["state"], 0) + 1
    attempts = sorted({r["attempts"] for r in rows})
    results = sorted({r["results"] for r in rows})
    return (
        f"states {dict(sorted(states.items()))}; attempts per job {attempts}; "
        f"AI results per job {results}"
    )


def worker(env: dict) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "ticket_api.worker", "--concurrency", "4"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=12)
    parser.add_argument("--stop-after", type=float, default=3.0)
    args = parser.parse_args(argv)
    env = {
        **os.environ,
        "JOB_LEASE_SECONDS": str(LEASE),
        "WORKER_DRAIN_SECONDS": "20",
        "LOG_LEVEL": "WARNING",
    }
    url = load_settings().database_url
    kill = signal.SIGKILL if hasattr(signal, "SIGKILL") else None
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        for name, how in (("graceful", signal.SIGTERM), ("killed", kill)):
            tag = f"Shutdown {name}"
            queue_tickets(args.jobs, tag)
            w = worker(env)
            time.sleep(args.stop_after)
            stopped = time.perf_counter()
            if how is None:
                w.terminate()
            else:
                w.send_signal(how)
            out, _ = w.communicate(timeout=60)
            exit_s = time.perf_counter() - stopped
            print(
                f"Round '{name}': stopped after {args.stop_after:.0f} s with "
                f"{'SIGTERM' if how == signal.SIGTERM else 'SIGKILL'}; the process ended "
                f"{exit_s:.1f} s later (exit code {w.returncode})"
            )
            for line in out.splitlines():
                if line.startswith(("Stopping", "Done")):
                    print(f"  worker said: {line}")
            print(f"  right after: {report(conn, tag)}")
            started = time.perf_counter()
            w2 = worker({**env, "WORKER_POLL_SECONDS": "0.5"})
            while True:
                left = conn.execute(
                    "SELECT count(*) AS n FROM jobs j JOIN tickets t USING (ticket_id)"
                    " WHERE t.subject LIKE %s AND j.state IN ('queued', 'running')",
                    (f"{tag} %",),
                ).fetchone()["n"]
                if left == 0 or time.perf_counter() - started > 120:
                    break
                time.sleep(0.5)
            w2.send_signal(signal.SIGTERM if hasattr(signal, "SIGTERM") else signal.SIGINT)
            w2.communicate(timeout=60)
            print(
                f"  a new worker finished the queue in {time.perf_counter() - started:.1f} s: "
                f"{report(conn, tag)}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
