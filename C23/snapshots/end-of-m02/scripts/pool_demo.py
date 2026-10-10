"""See what a connection pool does when it runs out, when code leaks a connection,
and when a transaction fails. Constructed cases, with a real pool and a real database.

    python -m scripts.pool_demo connect      the time to open a connection vs to borrow one
    python -m scripts.pool_demo exhaust      6 requests, a pool of 3, each holds a connection 2 s
    python -m scripts.pool_demo leak         code that forgets to give connections back
    python -m scripts.pool_demo rollback     a transaction that fails halfway
    python -m scripts.pool_demo all --json   every scenario, as JSON (for the explorer)
"""

import argparse
import json
import logging
import statistics
import sys
import threading
import time

import psycopg

from ticket_api.config import load_env, read_secret
from ticket_api.db import Database, DatabaseBusy

TICKET = "T-30002"


def connect(url: str, n: int = 50) -> dict:
    opened = []
    for _ in range(n):
        started = time.perf_counter()
        psycopg.connect(url).close()
        opened.append((time.perf_counter() - started) * 1000)
    db = Database(url, min_size=2, max_size=2)
    db.open()
    db.pool.wait()
    borrowed = []
    for _ in range(n):
        started = time.perf_counter()
        with db.connection():
            pass
        borrowed.append((time.perf_counter() - started) * 1000)
    db.close()
    return {
        "scenario": "connect",
        "n": n,
        "open_median_ms": round(statistics.median(opened), 2),
        "borrow_median_ms": round(statistics.median(borrowed), 3),
    }


def exhaust(
    url: str, requests: int = 6, size: int = 3, hold: float = 2.0, timeout: float = 1.0
) -> dict:
    db = Database(url, min_size=size, max_size=size, timeout=timeout)
    db.open()
    db.pool.wait()
    events, lock = [], threading.Lock()
    t0 = time.perf_counter()

    def request(i: int):
        asked = time.perf_counter() - t0
        try:
            with db.connection() as conn:
                got = time.perf_counter() - t0
                conn.execute("SELECT pg_sleep(%s)", (hold,))
            outcome = "ok"
        except DatabaseBusy:
            got = None
            outcome = "busy (503)"
        with lock:
            events.append(
                {
                    "request": i + 1,
                    "asked_s": round(asked, 2),
                    "got_connection_s": None if got is None else round(got, 2),
                    "finished_s": round(time.perf_counter() - t0, 2),
                    "outcome": outcome,
                }
            )

    threads = [threading.Thread(target=request, args=(i,)) for i in range(requests)]
    for t in threads:
        t.start()
        time.sleep(0.05)
    for t in threads:
        t.join()
    db.close()
    events.sort(key=lambda e: e["request"])
    return {
        "scenario": "exhaust",
        "pool_size": size,
        "timeout_s": timeout,
        "hold_s": hold,
        "events": events,
    }


def leak(url: str, size: int = 3, timeout: float = 1.0) -> dict:
    db = Database(url, min_size=size, max_size=size, timeout=timeout)
    db.open()
    db.pool.wait()
    steps = []

    def buggy_lookup(ticket_id: str):
        # The bug: a connection taken by hand and given back only on success.
        conn = db.pool.getconn()
        row = conn.execute(
            "SELECT subject FROM tickets WHERE ticket_id = %s", (ticket_id,)
        ).fetchone()
        if row is None:
            raise LookupError(ticket_id)  # returns without db.pool.putconn(conn)
        db.pool.putconn(conn)
        return row

    for i in range(size + 1):
        try:
            buggy_lookup("T-99999")  # a ticket that does not exist
        except LookupError:
            pass
        except Exception as error:  # noqa: BLE001 - shown to the learner
            steps.append({"call": i + 1, "result": type(error).__name__})
            continue
        s = db.stats()
        steps.append(
            {"call": i + 1, "result": "LookupError", "available": s["available"], "size": s["size"]}
        )
    started = time.perf_counter()
    try:
        with db.connection() as conn:
            conn.execute("SELECT 1")
        normal = "ok"
    except DatabaseBusy:
        normal = "busy (503)"
    steps.append(
        {
            "call": "a normal request",
            "result": normal,
            "waited_s": round(time.perf_counter() - started, 2),
        }
    )
    db.close()
    return {"scenario": "leak", "pool_size": size, "timeout_s": timeout, "steps": steps}


def rollback(url: str) -> dict:
    db = Database(url, min_size=2, max_size=2)
    db.open()
    db.pool.wait()
    with db.connection() as conn:
        before = conn.execute(
            "SELECT count(*) AS n FROM messages WHERE ticket_id = %s", (TICKET,)
        ).fetchone()["n"]
    error = None
    try:
        with db.connection() as conn:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO messages (tenant_id, ticket_id, author, body)"
                    " VALUES ('larkfield', %s, 'agent', 'Half done')",
                    (TICKET,),
                )
                # The second statement fails: 'robot' is not a known author (a CHECK constraint).
                conn.execute(
                    "INSERT INTO messages (tenant_id, ticket_id, author, body)"
                    " VALUES ('larkfield', %s, 'robot', 'x')",
                    (TICKET,),
                )
    except psycopg.errors.CheckViolation as e:
        error = str(e).strip().splitlines()[0]
    with db.connection() as conn:
        after = conn.execute(
            "SELECT count(*) AS n FROM messages WHERE ticket_id = %s", (TICKET,)
        ).fetchone()["n"]
    stats = db.stats()
    db.close()
    return {
        "scenario": "rollback",
        "error": error,
        "messages_before": before,
        "messages_after": after,
        "pool_after": stats,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenario", choices=["connect", "exhaust", "leak", "rollback", "all"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    load_env()
    logging.getLogger("ticket_api").setLevel(logging.ERROR)  # the demo prints what happens
    url = read_secret("DATABASE_URL")
    names = (
        ["connect", "exhaust", "leak", "rollback"] if args.scenario == "all" else [args.scenario]
    )
    results = [globals()[n](url) for n in names]
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    for r in results:
        print(f"== {r['scenario']}")
        if r["scenario"] == "connect":
            print(
                f"open a new connection: median {r['open_median_ms']} ms | borrow one from the"
                " pool:"
                f" median {r['borrow_median_ms']} ms ({r['n']} times each)"
            )
        elif r["scenario"] == "exhaust":
            print(
                f"pool of {r['pool_size']}, each request holds its connection {r['hold_s']} s,"
                f" a request waits at most {r['timeout_s']} s"
            )
            for e in r["events"]:
                got = "-" if e["got_connection_s"] is None else f"{e['got_connection_s']:.2f} s"
                print(
                    f"  request {e['request']}: asked at {e['asked_s']:.2f} s, connection at {got},"
                    f" done at {e['finished_s']:.2f} s: {e['outcome']}"
                )
        elif r["scenario"] == "leak":
            for s in r["steps"]:
                if "available" in s:
                    print(
                        f"  call {s['call']}: {s['result']}; connections free:"
                        f" {s['available']} of {s['size']}"
                    )
                else:
                    extra = f" after {s['waited_s']} s" if "waited_s" in s else ""
                    call = s["call"] if isinstance(s["call"], str) else f"call {s['call']}"
                    print(f"  {call}: {s['result']}{extra}")
        else:
            print(f"  error: {r['error']}")
            print(
                f"  messages on {TICKET}: {r['messages_before']} before, {r['messages_after']}"
                " after"
                f" | pool: {r['pool_after']['available']} of {r['pool_after']['size']}"
                " connections free"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
