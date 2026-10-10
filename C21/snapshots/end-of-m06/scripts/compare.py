"""Compare configurations of the service under the same workload, with several passes.

    python -m scripts.compare \
        --config "one process:INTAKE_MODE=async" \
        --config "queue, 2 workers:INTAKE_MODE=queue,WORKERS=2" \
        --users 8 --seconds 40 --warmup 10 --passes 3 [--pace 0] [--json result.json] \
        [--port 8790]

For each configuration and pass it starts everything again from the same state: the
small data loaded again, the cache's keys deleted, the simulated provider reset; then
the API (uvicorn on 127.0.0.1:8790 or --port/COMPARE_PORT, WEB_WORKERS processes) and,
with INTAKE_MODE=queue, WORKERS worker processes; then Locust (loadtest/locustfile.py,
headless) for --seconds. A configuration is "name:VAR=value,VAR=value": any setting of
the API (.env.example, README), plus WEB_WORKERS and WORKERS.

It reports, per configuration, the median of the passes and the range (lowest-highest):
- useful throughput: successful answers within --slo-ms (5 s) per second;
- throughput: tickets whose AI work finished per second (201 answers; for the queue, jobs
  that succeeded), after the warm-up;
- the request latency p50/p95/p99 (exact, from Locust's samples) and the errors;
- for the queue: the time from submit to result (p50/p95), and the queue left at the end;
- the API processes' CPU use, the provider's refusals (429), the AI cost per ticket.
Run it only on your own computer, with nothing else heavy running (python -m scripts.machine).
The simulated provider must run (python -m simulator); its quota mode is your choice:
write it down with the result.
"""

import argparse
import csv
import json
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import psutil
import psycopg
import redis
from psycopg.rows import dict_row

from scripts import cost, load, machine, percentiles
from scripts.breakdown import provider_stats
from ticket_api.config import load_settings

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("COMPARE_PORT", "8790"))


def parse_config(text: str) -> tuple[str, dict]:
    name, _, rest = text.partition(":")
    env = dict(item.split("=", 1) for item in rest.split(",") if item.strip())
    return name.strip(), {k.strip(): v.strip() for k, v in env.items()}


def wait_until_up(url: str, seconds: float = 30) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if httpx.get(url + "/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise SystemExit("The API did not start: see the output above.")


def start(env: dict, port: int = PORT) -> tuple[subprocess.Popen, list[subprocess.Popen]]:
    full = {**os.environ, "LOG_LEVEL": "WARNING", "RATE_LIMIT_PER_MINUTE": "0", **env}
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ticket_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--workers",
            env.get("WEB_WORKERS", "1"),
            "--log-level",
            "warning",
        ],
        cwd=ROOT,
        env=full,
    )
    workers = []
    if env.get("INTAKE_MODE", "queue") == "queue":
        for _ in range(int(env.get("WORKERS", "1"))):
            workers.append(
                subprocess.Popen(
                    [sys.executable, "-m", "ticket_api.worker"],
                    cwd=ROOT,
                    env=full,
                    stdout=subprocess.DEVNULL,
                )
            )
    return api, workers


def stop(procs: list[subprocess.Popen]) -> None:
    for p in procs:
        if p.poll() is None:
            p.send_signal(signal.SIGTERM if hasattr(signal, "SIGTERM") else signal.SIGINT)
    for p in procs:
        try:
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            p.kill()


def cpu_seconds(procs: list[subprocess.Popen]) -> float:
    total = 0.0
    for p in procs:
        try:
            ps = psutil.Process(p.pid)
            for q in [ps, *ps.children(recursive=True)]:
                t = q.cpu_times()
                total += t.user + t.system
        except psutil.NoSuchProcess:
            pass
    return total


def reset(settings, provider_url: str) -> None:
    load.load(settings.database_url, "small", reset=True, quiet=True, files=False)
    if settings.cache_url:
        r = redis.Redis.from_url(settings.cache_url)
        keys = list(r.scan_iter("ta:*", count=1000))
        if keys:
            r.delete(*keys)
    httpx.post(provider_url.rsplit("/v1", 1)[0] + "/admin/reset", timeout=5)


def one_pass(name: str, env: dict, args, settings) -> dict:
    provider_url = env.get("PROVIDER_URL", settings.provider_url)
    reset(settings, provider_url)
    api, workers = start(env, args.port)
    try:
        wait_until_up(f"http://127.0.0.1:{args.port}")
        before = provider_stats(provider_url)
        cpu0, wall0 = cpu_seconds([api]), time.monotonic()
        with tempfile.TemporaryDirectory() as tmp:
            samples = Path(tmp) / "samples.csv"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "locust",
                    "-f",
                    str(ROOT / "loadtest/locustfile.py"),
                    "--headless",
                    "-u",
                    str(args.users),
                    "-r",
                    str(args.users),
                    "-t",
                    f"{args.seconds}s",
                    "--host",
                    f"http://127.0.0.1:{args.port}",
                    "--only-summary",
                    "--loglevel",
                    "WARNING",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                env={**os.environ, "SAMPLES_CSV": str(samples), "PACE_SECONDS": str(args.pace)},
            )
            cpu = (cpu_seconds([api]) - cpu0) / (time.monotonic() - wall0)
            rows = list(csv.DictReader(open(samples, encoding="utf-8")))
        t0 = min(float(r["start"]) for r in rows)
        window = (t0 + args.warmup, t0 + args.seconds)
        summary = percentiles.summarize(rows, skip=args.warmup)
        # Useful throughput: successful answers that came within the time users accept.
        measured = [r for r in rows if float(r["start"]) >= window[0]]
        useful = sum(
            1 for r in measured if 200 <= int(r["status"]) < 300 and float(r["ms"]) <= args.slo_ms
        )
        summary["useful_per_s"] = round(useful / summary["seconds"], 2) if summary["seconds"] else 0
        out = {"config": name, "env": env, **summary, "api_cpu_percent": round(cpu * 100, 1)}
        with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
            if workers:
                # Jobs submitted in the measured window: did they finish, and how long did it take?
                drain_until = time.monotonic() + args.drain
                while time.monotonic() < drain_until:
                    left = conn.execute(
                        "SELECT count(*) AS n FROM jobs WHERE state IN ('queued', 'running')"
                    ).fetchone()["n"]
                    if left == 0:
                        break
                    time.sleep(1)
                jobs = conn.execute(
                    "SELECT state, extract(epoch FROM created_at) AS created,"
                    " extract(epoch FROM finished_at - created_at) * 1000 AS e2e_ms,"
                    " extract(epoch FROM finished_at) AS finished FROM jobs"
                ).fetchall()
                done = sorted(
                    float(j["e2e_ms"])
                    for j in jobs
                    if j["state"] == "succeeded" and window[0] <= j["created"] < window[1]
                )
                finished_in_window = sum(
                    1
                    for j in jobs
                    if j["state"] == "succeeded" and window[0] <= j["finished"] < window[1]
                )
                out["work_done_per_s"] = round(finished_in_window / (window[1] - window[0]), 2)
                out["e2e_p50_ms"] = percentiles.nearest_rank(done, 50) if done else None
                out["e2e_p95_ms"] = percentiles.nearest_rank(done, 95) if done else None
                out["jobs_left_after_drain"] = sum(
                    1 for j in jobs if j["state"] in ("queued", "running")
                )
                out["jobs_by_state"] = {
                    s: sum(1 for j in jobs if j["state"] == s)
                    for s in sorted({j["state"] for j in jobs})
                }
            else:
                out["work_done_per_s"] = summary["throughput_ok_per_s"]
            c = cost.per_ticket(conn, None)
            out["ai_usd_per_ticket"] = (
                round(c["ai_usd"] / c["tickets"], 8) if c["tickets"] else None
            )
        after = provider_stats(provider_url)
        if before and after:

            def refused(s: dict) -> int:
                return sum(d.get("429", 0) for d in s["calls"].values())

            out["provider_429"] = refused(after) - refused(before)
            out["provider_max_in_flight"] = after["max_in_flight"]
        return out
    finally:
        stop(workers + [api])


def median_and_range(passes: list[dict], key: str):
    values = [p[key] for p in passes if p.get(key) is not None]
    if not values:
        return None
    m = statistics.median(values)
    return {"median": round(m, 2) if abs(m) >= 0.01 else m, "min": min(values), "max": max(values)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", action="append", required=True)
    parser.add_argument("--users", type=int, default=8)
    parser.add_argument("--pace", type=float, default=0.0, help="PACE_SECONDS of each user")
    parser.add_argument("--seconds", type=int, default=40)
    parser.add_argument("--warmup", type=float, default=10)
    parser.add_argument("--drain", type=float, default=120, help="seconds to wait for the queue")
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument(
        "--slo-ms",
        type=float,
        default=5000,
        help="an answer slower than this is not useful (default 5 s)",
    )
    parser.add_argument("--json", help="write every pass and the summary here")
    parser.add_argument(
        "--port", type=int, default=PORT, help="the API's port during the run (default 8790)"
    )
    args = parser.parse_args(argv)
    settings = load_settings()
    configs = [parse_config(c) for c in args.config]
    result = {
        "machine": machine.describe(),
        "workload": {
            "locustfile": "loadtest/locustfile.py",
            "users": args.users,
            "pace_seconds": args.pace,
            "seconds": args.seconds,
            "warmup_seconds": args.warmup,
            "passes": args.passes,
        },
        "configs": [],
    }
    keys = [
        "work_done_per_s",
        "throughput_ok_per_s",
        "useful_per_s",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "e2e_p50_ms",
        "e2e_p95_ms",
        "api_cpu_percent",
        "provider_429",
        "ai_usd_per_ticket",
    ]
    for name, env in configs:
        passes = []
        for i in range(args.passes):
            p = one_pass(name, env, args, settings)
            passes.append(p)
            print(
                f"{name} pass {i + 1}: done {p['work_done_per_s']}/s, p95 {p['p95_ms']} ms, "
                f"codes {p['statuses']}",
                flush=True,
            )
        summary = {k: median_and_range(passes, k) for k in keys}
        result["configs"].append({"name": name, "env": env, "passes": passes, "summary": summary})
    print(
        f"\nMedian of {args.passes} passes (lowest-highest); {args.users} users, pace "
        f"{args.pace} s, {args.seconds} s, first {args.warmup:g} s left out"
    )
    for c in result["configs"]:
        s = c["summary"]

        def f(k, s=s):
            v = s.get(k)
            return "-" if v is None else f"{v['median']:g} ({v['min']:g}-{v['max']:g})"

        print(
            f"- {c['name']}: done per s {f('work_done_per_s')} | p50 {f('p50_ms')} ms | "
            f"p95 {f('p95_ms')} ms | p99 {f('p99_ms')} ms"
            + (f" | submit to result p95 {f('e2e_p95_ms')} ms" if s.get("e2e_p95_ms") else "")
            + f" | API CPU {f('api_cpu_percent')}% | 429 from provider {f('provider_429')}"
        )
    if args.json:
        Path(args.json).write_text(
            json.dumps(result, indent=1, default=str) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
