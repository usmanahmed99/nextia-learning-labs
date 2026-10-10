"""Measure an endpoint under a fixed workload: the same requests, in the same order, every time.

    python -m scripts.bench                                the ticket list: 200 requests, 4 at once
    python -m scripts.bench --requests 400 --concurrency 16
    python -m scripts.bench --pool off                     a new connection for every request
    python -m scripts.bench --path "/v1/tenants/larkfield/tickets/T-399000"  another endpoint
    python -m scripts.bench --tenant bramble --user usr-ines   another organization and person
    python -m scripts.bench --row-security off             without the second lock (to compare)
    python -m scripts.bench --json result.json             also save every number

It starts the API in this process (on 127.0.0.1:8765, one worker, with your .env
settings and DATABASE_URL), sends a few warm-up requests, then the workload, and
prints the median, the 95th percentile (p95: 95 of 100 requests were faster) and
the slowest time, the errors, and the database queries per request. Since the
authentication course, every request sends an access token of --user (made with
the practice provider's keys in .idp/), and the paths are under the organization. Run it with
nothing else busy on the computer, and compare runs with the same data and the
same workload only.
"""

import argparse
import json
import logging
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import uvicorn

from scripts.practice import connect, token
from ticket_api.config import load_settings
from ticket_api.main import create_app

PORT = 8765
TEAMS = ["billing", "shipping", "other", "account", "login"]


def default_paths(tenant: str) -> list[str]:
    return [f"/v1/tenants/{tenant}/tickets?status=open&team={t}&limit=20" for t in TEAMS]


def percentile(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[max(0, int(round(p * len(values))) - 1)]


def serve(app) -> uvicorn.Server:
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning", access_log=False)
    )
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.05)
    raise SystemExit("The API did not start.")


def call(path: str, key: str | None, bearer: str | None = None) -> tuple[float, int, int]:
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}")
    if key:
        request.add_header("X-API-Key", key)
    if bearer:
        request.add_header("Authorization", f"Bearer {bearer}")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
            status, queries = response.status, int(response.headers.get("X-DB-Queries", -1))
    except urllib.error.HTTPError as error:
        error.read()
        status, queries = error.code, int(error.headers.get("X-DB-Queries", -1))
    return (time.perf_counter() - started) * 1000, status, queries


def run(
    paths: list[str],
    requests: int,
    concurrency: int,
    pool: bool,
    pool_max: int,
    pool_timeout: float,
    warmup: int = 10,
    user: str = "usr-grace",
    row_security: bool = True,
) -> dict:
    settings = load_settings()
    settings = replace(
        settings,
        db_pool=pool,
        db_pool_max=pool_max,
        db_pool_min=min(2, pool_max),
        db_pool_timeout=pool_timeout,
        show_query_count=True,
        log_level="WARNING",
        db_row_security=row_security,
    )
    app = create_app(settings)
    connect(app)  # the practice provider's keys, from .idp/
    bearer = token(user)
    logging.getLogger("ticket_api").setLevel(logging.WARNING)  # no line per request
    server = serve(app)
    try:
        work = [paths[i % len(paths)] for i in range(requests)]
        for p in work[:warmup]:
            call(p, settings.api_key, bearer)
        started = time.perf_counter()
        with ThreadPoolExecutor(concurrency) as ex:
            results = list(ex.map(lambda p: call(p, settings.api_key, bearer), work))
        wall = time.perf_counter() - started
        stats = app.state.db.stats() if app.state.db else {}
    finally:
        server.should_exit = True
        time.sleep(0.3)
    times = [r[0] for r in results]
    ok = [r for r in results if r[1] == 200]
    codes = {}
    for r in results:
        codes[r[1]] = codes.get(r[1], 0) + 1
    return {
        "requests": requests,
        "concurrency": concurrency,
        "pool": pool,
        "pool_max": pool_max,
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": round(percentile(times, 0.95), 1),
        "max_ms": round(max(times), 1),
        "per_second": round(requests / wall, 1),
        "status_codes": codes,
        "errors": requests - len(ok),
        "queries_per_request": sorted({r[2] for r in ok}),
        "pool_stats": stats,
        "paths": paths,
        "user": user,
        "row_security": row_security,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--path", action="append", help="a path to request (repeat for several)")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--pool", choices=["on", "off"], default="on")
    parser.add_argument("--pool-max", type=int, default=10)
    parser.add_argument("--pool-timeout", type=float, default=5.0)
    parser.add_argument("--tenant", default="larkfield", help="the organization of the list")
    parser.add_argument("--user", default="usr-grace", help="the person who calls")
    parser.add_argument("--row-security", choices=["on", "off"], default="on")
    parser.add_argument("--json", help="save the result to this file")
    args = parser.parse_args(argv)
    result = run(
        args.path or default_paths(args.tenant),
        args.requests,
        args.concurrency,
        args.pool == "on",
        args.pool_max,
        args.pool_timeout,
        user=args.user,
        row_security=args.row_security == "on",
    )
    print(
        f"{result['requests']} requests, {result['concurrency']} at a time, pool {args.pool}"
        + (f" (max {args.pool_max})" if args.pool == "on" else "")
    )
    print(
        f"median {result['median_ms']} ms | p95 {result['p95_ms']} ms | slowest"
        f" {result['max_ms']} ms"
        f" | {result['per_second']} requests/s"
    )
    print(
        f"errors: {result['errors']} {result['status_codes']} | database queries per request:"
        f" {', '.join(map(str, result['queries_per_request']))}"
    )
    if args.json:
        with open(args.json, "w") as f:
            json.dump(result, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
