"""Replay real arrival times from a public 311 trace against your local ticket API.

    python -m scripts.replay_trace --start "2025-07-15 10:49:47" --minutes 4

Nextia Learning, Scaling APIs and AI Workloads, case study "Capacity plan from a public
traffic trace". Copy this file into the project's scripts/ folder (the project at the end
of Module 6). Run it only against the API on your own computer.

Each request of the trace (San Francisco 311, 2025, ODC PDDL 1.0) becomes one new ticket,
sent at the same moment after --start as in the trace: an open workload, like
scripts.send_tickets, but with real gaps and real bursts. Only the times are real; the
ticket texts are the course's made-up practice tickets. At the end, the script reads the
jobs from PostgreSQL and prints how long each one waited before a worker took it.

If the trace file is not in the current folder, the script downloads it from the course's
labs repository (about 4 MB) and checks its SHA-256.
"""

import argparse
import asyncio
import csv
import gzip
import hashlib
import os
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import psycopg

from scripts.breakdown import tickets
from scripts.percentiles import nearest_rank
from ticket_api.config import load_env, load_settings

FILE = "sf311_2025_arrivals.csv.gz"
SHA256 = "57c4209ce8aefb694a99436faef07d3eb6256e1004724fc5ec358ccdc720e548"
URL = ("https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C21/"
       "M07-L01-capacity-plan-from-a-public-traffic-trace/" + FILE)


def trace_file(path: Path) -> Path:
    """The trace, downloaded once and checked."""
    if not path.exists():
        print(f"Downloading {FILE} (about 4 MB) ...", flush=True)
        urllib.request.urlretrieve(URL, path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise SystemExit(f"{path} has the wrong checksum. Delete it and run again.")
    return path


def arrivals(path: Path, start: datetime, minutes: float) -> list[tuple[float, datetime]]:
    """(seconds after start, time) for each request in the window; Test rows left out."""
    end = start + timedelta(minutes=minutes)
    out = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["source"] == "Test":
                continue
            t = datetime.fromisoformat(row["requested_datetime"])
            if start <= t < end:
                out.append(((t - start).total_seconds(), t))
    return out


async def send(url: str, plan: list[tuple[float, datetime]], headers: dict) -> tuple[Counter, list]:
    statuses: Counter = Counter()
    job_ids: list[int] = []
    pool = tickets(min(len(plan), 200))
    async with httpx.AsyncClient(base_url=url, headers=headers, timeout=60,
                                 limits=httpx.Limits(max_connections=100)) as client:

        async def one(i: int) -> None:
            try:
                r = await client.post("/v1/tickets", json=pool[i % len(pool)])
            except httpx.HTTPError as error:
                statuses[type(error).__name__] += 1
                return
            statuses[r.status_code] += 1
            if r.status_code == 202:
                job_ids.append(r.json()["job_id"])

        tasks = []
        t0 = time.perf_counter()
        for i, (offset, _) in enumerate(plan):
            delay = t0 + offset - time.perf_counter()
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(one(i)))
        await asyncio.gather(*tasks)
    return statuses, job_ids


def read_jobs(database_url: str, job_ids: list[int], timeout: float = 300) -> list[dict]:
    """Wait until every job has finished, then read its times."""
    query = ("SELECT job_id, state, created_at, started_at, finished_at FROM jobs"
             " WHERE job_id = ANY(%s) ORDER BY job_id")
    deadline = time.monotonic() + timeout
    with psycopg.connect(database_url, autocommit=True) as conn:
        while True:
            rows = conn.execute(query, (job_ids,)).fetchall()
            if all(r[4] is not None for r in rows) or time.monotonic() > deadline:
                break
            time.sleep(1)
    keys = ["job_id", "state", "created_at", "started_at", "finished_at"]
    return [dict(zip(keys, r)) for r in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", required=True, help='trace time, for example "2025-07-15 10:49:47"')
    parser.add_argument("--minutes", type=float, default=4.0)
    parser.add_argument("--file", default=FILE)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--csv", help="also write each job's wait to this CSV file")
    args = parser.parse_args(argv)
    load_env()
    headers = {"X-API-Key": os.environ["API_KEY"]} if os.environ.get("API_KEY") else {}
    start = datetime.fromisoformat(args.start)
    plan = arrivals(trace_file(Path(args.file)), start, args.minutes)
    if not plan:
        raise SystemExit("No requests in that window.")
    per_second = Counter(t for _, t in plan)
    burst_time, burst_size = per_second.most_common(1)[0]
    print(f"Replaying {len(plan)} requests from {start} for {args.minutes:g} minutes "
          f"(largest same-second group: {burst_size} at {burst_time:%H:%M:%S}) ...", flush=True)
    statuses, job_ids = asyncio.run(send(args.url, plan, headers))
    print(f"Sent: status codes {dict(sorted(statuses.items(), key=lambda x: str(x[0])))}")
    jobs = read_jobs(load_settings().database_url, job_ids)
    states = Counter(j["state"] for j in jobs)
    waits = sorted((j["started_at"] - j["created_at"]).total_seconds() for j in jobs if j["started_at"])
    print(f"Jobs: {dict(states)}")
    print(f"Wait before a worker took the job (s): median {nearest_rank(waits, 50):.1f}, "
          f"p95 {nearest_rank(waits, 95):.1f}, max {waits[-1]:.1f}")
    events = sorted([(j["created_at"], 1) for j in jobs] + [(j["started_at"], -1) for j in jobs if j["started_at"]])
    waiting = peak = 0
    for _, step in events:
        waiting += step
        peak = max(peak, waiting)
    print(f"Most jobs waiting at once: {peak}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["job_id", "state", "wait_seconds", "work_seconds"])
            for j in jobs:
                wait = (j["started_at"] - j["created_at"]).total_seconds() if j["started_at"] else ""
                work = (j["finished_at"] - j["started_at"]).total_seconds() if j["finished_at"] and j["started_at"] else ""
                w.writerow([j["job_id"], j["state"], wait, work])
        print(f"Wrote {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
