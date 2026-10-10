"""A small autoscaler on your computer: it starts and stops worker processes from the queue.

    python -m scripts.autoscale [--min 1] [--max 6] [--per-worker 8] [--cooldown 30]
                                [--signal backlog|age] [--seconds 120] [--log autoscale.csv]

Every --every seconds it reads the queue (python -m scripts.queue_watch shows the same
numbers) and decides how many workers there should be:
- signal backlog (queue length): workers = ceil((ready + running) / per-worker), as KEDA's
  queue scalers do with a target value per replica;
- signal age: one more worker while the oldest queued job is older than --target-age
  seconds; one less when nothing waits.
It always stays between --min and --max. It adds workers at once, but removes one only
after the wish to remove has lasted --cooldown seconds (so a short dip does not stop a
worker that is needed again a moment later). A new worker is a new process: the time until
it can work is its cold start (printed). Workers are stopped with SIGTERM (graceful).
This is a local simulation of what a platform autoscaler does (Module 5).
"""

import argparse
import csv
import math
import os
import signal
import subprocess
import sys
import threading
import time

import psycopg
from psycopg.rows import dict_row

from ticket_api import jobs
from ticket_api.config import load_settings


class Workers:
    def __init__(self, concurrency: int):
        self.procs: list[subprocess.Popen] = []
        self.concurrency = concurrency
        self.cold_starts: list[float] = []

    def start(self) -> None:
        started = time.perf_counter()
        p = subprocess.Popen(
            [sys.executable, "-m", "ticket_api.worker", "--concurrency", str(self.concurrency)],
            env={**os.environ, "LOG_LEVEL": "WARNING", "PYTHONUNBUFFERED": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        def ready() -> None:  # the worker prints its first line when it can take jobs
            p.stdout.readline()
            self.cold_starts.append(time.perf_counter() - started)
            for _ in p.stdout:  # keep reading so the pipe never fills
                pass

        threading.Thread(target=ready, daemon=True).start()
        self.procs.append(p)

    def stop_one(self) -> None:
        p = self.procs.pop()
        p.send_signal(signal.SIGTERM if hasattr(signal, "SIGTERM") else signal.SIGINT)

    def stop_all(self) -> None:
        while self.procs:
            self.stop_one()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min", type=int, default=1)
    parser.add_argument("--max", type=int, default=6)
    parser.add_argument("--signal", choices=["backlog", "age"], default="backlog")
    parser.add_argument("--per-worker", type=float, default=8, help="backlog per worker")
    parser.add_argument("--target-age", type=float, default=10, help="seconds (signal age)")
    parser.add_argument("--cooldown", type=float, default=30)
    parser.add_argument("--every", type=float, default=2)
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--worker-concurrency", type=int, default=4)
    parser.add_argument("--log", help="write one CSV line per check")
    args = parser.parse_args(argv)
    workers = Workers(args.worker_concurrency)
    for _ in range(args.min):
        workers.start()
    low_since: float | None = None
    rows = []
    t0 = time.monotonic()
    print(f"{'time':>5} {'ready':>6} {'running':>8} {'oldest':>7} {'workers':>8} {'wanted':>7}")
    try:
        with psycopg.connect(
            load_settings().database_url, autocommit=True, row_factory=dict_row
        ) as conn:
            while time.monotonic() - t0 < args.seconds:
                s = jobs.stats(conn)
                n = len(workers.procs)
                if args.signal == "backlog":
                    wanted = math.ceil((s["ready"] + s["running"]) / args.per_worker)
                elif s["oldest_queued_seconds"] > args.target_age:
                    wanted = n + 1
                else:
                    wanted = n - 1 if s["ready"] == 0 and s["running"] == 0 else n
                wanted = max(args.min, min(args.max, wanted))
                event = ""
                if wanted > n:
                    for _ in range(wanted - n):
                        workers.start()
                    event, low_since = f"+{wanted - n}", None
                elif wanted < n:
                    low_since = low_since or time.monotonic()
                    if time.monotonic() - low_since >= args.cooldown:
                        workers.stop_one()
                        event, low_since = "-1", time.monotonic()
                else:
                    low_since = None
                t = time.monotonic() - t0
                print(
                    f"{t:>5.0f} {s['ready']:>6} {s['running']:>8} "
                    f"{s['oldest_queued_seconds']:>7.1f} {len(workers.procs):>8} {wanted:>7} "
                    f"{event}",
                    flush=True,
                )
                rows.append(
                    {
                        "t": round(t, 1),
                        **s,
                        "workers": len(workers.procs),
                        "wanted": wanted,
                        "event": event,
                    }
                )
                time.sleep(args.every)
    except KeyboardInterrupt:
        pass
    finally:
        workers.stop_all()
    if workers.cold_starts:
        cs = sorted(workers.cold_starts)
        print(
            f"Cold start of a worker (process start until it can take jobs): median "
            f"{cs[len(cs) // 2]:.2f} s, slowest {cs[-1]:.2f} s ({len(cs)} starts)"
        )
    if args.log and rows:
        with open(args.log, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
