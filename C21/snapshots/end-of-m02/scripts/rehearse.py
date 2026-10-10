"""Rehearse migrations on a copy with representative data, before you run them for real.

    python -m scripts.rehearse                       the pending migrations, on the large data
    python -m scripts.rehearse --from 005            from migration 005 on (also applied ones)
    python -m scripts.rehearse --size small --keep   on the small data; keep the copy afterwards

It makes a separate database (<your database>_rehearsal), applies the migrations
before the first one to test, loads the data, and then applies the rest one at a
time. While each one runs, a reader asks for one row by key, every 10 ms, from
each help-desk table: the longest wait shows how long the migration blocked
normal reads. Your own database does not change.
"""

import argparse
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

import psycopg

from scripts import load
from ticket_api import migrate
from ticket_api.config import load_env, read_secret

READS = {
    "tickets": "SELECT 1 FROM tickets WHERE ticket_id = (SELECT min(ticket_id) FROM tickets)",
    "messages": "SELECT 1 FROM messages WHERE message_id = 1",
    "ai_runs": "SELECT 1 FROM ai_runs WHERE run_id = 1",
    "attachments": "SELECT 1 FROM attachments LIMIT 1",
}


def reader(url: str, table: str, stop: threading.Event, waits: list[float]) -> None:
    with psycopg.connect(url, autocommit=True) as conn:
        while not stop.is_set():
            started = time.perf_counter()
            conn.execute(READS[table]).fetchall()
            waits.append(time.perf_counter() - started)
            time.sleep(0.01)


def rehearse(url: str, size: str, first: str | None, keep: bool, lock_timeout: str) -> list[dict]:
    base, name = url.rsplit("/", 1)
    target = f"{name}_rehearsal"
    with psycopg.connect(url) as conn:
        try:
            applied = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        except psycopg.errors.UndefinedTable:
            applied = set()
    files = sorted(migrate.MIGRATIONS.glob("*.sql"))
    if first is None:
        todo = [f for f in files if f.stem not in applied]
    else:
        todo = [f for f in files if f.stem >= first]
    if not todo:
        print(
            "No migration to rehearse: every migration is applied. Use --from NNN to test"
            " applied ones."
        )
        return []
    before = [f for f in files if f.stem < todo[0].stem]
    with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {target} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {target}")
    copy_url = f"{base}/{target}"
    folder = Path(tempfile.mkdtemp(prefix="migrations-"))
    for f in before:
        shutil.copy(f, folder / f.name)
    real = migrate.MIGRATIONS
    migrate.MIGRATIONS = folder
    try:
        upto = before[-1].stem if before else "none"
        print(f"Loading the {size} data into {target} (migrations up to {upto}) ...")
        load.load(copy_url, size, quiet=True)
    finally:
        migrate.MIGRATIONS = real
    results = []
    print(
        f"{'migration':<32} {'seconds':>8}  longest read wait (s): "
        + "  ".join(f"{t:>11}" for t in READS)
    )
    for f in todo:
        stop, waits = threading.Event(), {t: [] for t in READS}
        threads = [
            threading.Thread(target=reader, args=(copy_url, t, stop, waits[t])) for t in READS
        ]
        for th in threads:
            th.start()
        time.sleep(0.3)
        started = time.perf_counter()
        error = None
        try:
            migrate.apply(copy_url, f, lock_timeout)
        except (psycopg.Error, migrate.MigrationError) as e:
            error = str(e).strip().splitlines()[0]
        seconds = time.perf_counter() - started
        time.sleep(0.3)
        stop.set()
        for th in threads:
            th.join()
        row = {
            "migration": f.stem,
            "seconds": round(seconds, 3),
            "error": error,
            "longest_read_wait": {t: round(max(w), 3) for t, w in waits.items()},
        }
        results.append(row)
        print(
            f"{f.stem:<32} {seconds:>8.2f}  "
            + " " * 24
            + "  ".join(f"{row['longest_read_wait'][t]:>11.2f}" for t in READS)
        )
        if error:
            print(f"  FAILED: {error}")
            break
    if not keep:
        with psycopg.connect(f"{base}/postgres", autocommit=True) as conn:
            conn.execute(f"DROP DATABASE IF EXISTS {target} WITH (FORCE)")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", choices=["small", "large"], default="large")
    parser.add_argument("--from", dest="first", help="the first migration to test, for example 005")
    parser.add_argument("--keep", action="store_true", help="keep the rehearsal database")
    parser.add_argument("--lock-timeout", default="60s")
    args = parser.parse_args(argv)
    load_env()
    url = read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    first = None
    if args.first:
        matches = [f.stem for f in migrate.MIGRATIONS.glob(f"{args.first}*.sql")]
        if not matches:
            print(f"No migration starts with {args.first}.", file=sys.stderr)
            return 1
        first = matches[0]
    results = rehearse(url, args.size, first, args.keep, args.lock_timeout)
    return 1 if any(r["error"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
