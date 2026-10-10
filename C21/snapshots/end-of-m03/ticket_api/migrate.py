"""Apply the database migrations in migrations/, in order, once each.

    python -m ticket_api.migrate            apply every migration that is not applied yet
    python -m ticket_api.migrate --status   list the migrations and whether they are applied

Reads the database from DATABASE_URL or DATABASE_URL_FILE. Each migration runs
in its own transaction, and its name and checksum are recorded in
schema_migrations. Rules:

- A migration that was applied must never change: write a new one. If its
  file changed, nothing runs and the command says which file.
- A migration waits at most MIGRATION_LOCK_TIMEOUT (default 5s) for a lock. A
  migration that waits longer stops, instead of blocking every query that
  comes after it.
- A file whose first line is "-- migrate: no-transaction" runs outside a
  transaction, one statement at a time (CREATE INDEX CONCURRENTLY needs this).
  If it fails halfway, an index can stay behind as INVALID: the command checks
  for that and stops.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import psycopg

from ticket_api.config import load_env, read_secret

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
NO_TRANSACTION = "-- migrate: no-transaction"

CREATE_LOG = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text        PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum text
"""


class MigrationError(Exception):
    """A migration cannot run safely."""


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending(conn: psycopg.Connection) -> tuple[list[Path], dict[str, str | None]]:
    conn.execute("SET client_min_messages = warning")
    conn.execute(CREATE_LOG)
    applied = dict(conn.execute("SELECT version, checksum FROM schema_migrations").fetchall())
    files = sorted(MIGRATIONS.glob("*.sql"))
    for f in files:
        if f.stem not in applied:
            continue
        if applied[f.stem] is None:  # applied by an older migrate.py: record its checksum now
            conn.execute(
                "UPDATE schema_migrations SET checksum = %s WHERE version = %s",
                (checksum(f), f.stem),
            )
        elif applied[f.stem] != checksum(f):
            raise MigrationError(
                f"{f.name} was changed after it was applied. "
                "Put it back as it was, and write the change as a new migration."
            )
    return [f for f in files if f.stem not in applied], applied


def statements(sql: str) -> list[str]:
    """Split a no-transaction file into statements (simple files only: no functions)."""
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def apply(url: str, path: Path, lock_timeout: str) -> None:
    sql = path.read_text(encoding="utf-8")
    record = "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)"
    if sql.startswith(NO_TRANSACTION):
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(f"SET lock_timeout = '{lock_timeout}'")
            for statement in statements(sql):
                conn.execute(statement)
            invalid = conn.execute(
                "SELECT indexrelid::regclass::text FROM pg_index WHERE NOT indisvalid"
            ).fetchall()
            if invalid:
                raise MigrationError(
                    f"{path.name} left an invalid index: {', '.join(r[0] for r in invalid)}. "
                    "Drop it (DROP INDEX CONCURRENTLY name) and run the migrations again."
                )
            conn.execute(record, (path.stem, checksum(path)))
        return
    with psycopg.connect(url) as conn:
        with conn.transaction():
            conn.execute(f"SET LOCAL lock_timeout = '{lock_timeout}'")
            conn.execute(sql)
            conn.execute(record, (path.stem, checksum(path)))


def main(argv: list[str] | None = None, url: str | None = None, quiet: bool = False) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true", help="only list the migrations")
    args = parser.parse_args(argv)

    load_env()
    url = url or read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set: nothing to migrate.", file=sys.stderr)
        return 1
    lock_timeout = os.environ.get("MIGRATION_LOCK_TIMEOUT", "5s")
    current = None
    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            todo, applied = pending(conn)
            conn.commit()
        if args.status:
            for f in sorted(MIGRATIONS.glob("*.sql")):
                print(f"{'applied' if f.stem in applied else 'pending'}  {f.stem}")
            return 0
        for current in todo:
            apply(url, current, lock_timeout)
            if not quiet:
                print(f"applied  {current.stem}")
    except MigrationError as error:
        print(f"Migration stopped: {error}", file=sys.stderr)
        return 1
    except psycopg.errors.LockNotAvailable:
        print(
            f"Migration stopped: {current.name} waited more than {lock_timeout} for a lock. "
            "Another transaction is using the table. Try again when it is quiet.",
            file=sys.stderr,
        )
        return 1
    except psycopg.Error as error:
        first = str(error).strip().splitlines()[0]
        print(f"Migration stopped: {current.name} failed: {first}", file=sys.stderr)
        return 1
    if not quiet:
        print(f"Database is up to date ({len(applied) + len(todo)} migrations).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
