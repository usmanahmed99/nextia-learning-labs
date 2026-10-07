"""Apply the database migrations in migrations/, in order, once each.

    python -m ticket_api.migrate            apply every migration that is not applied yet
    python -m ticket_api.migrate --status   list the migrations and whether they are applied

Reads the database from DATABASE_URL or DATABASE_URL_FILE. Each migration runs
in its own transaction, and its name is recorded in schema_migrations.
"""

import argparse
import sys
from pathlib import Path

import psycopg

from ticket_api.config import read_secret

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"

CREATE_LOG = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text        PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def pending(conn: psycopg.Connection) -> tuple[list[Path], set[str]]:
    conn.execute(CREATE_LOG)
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    files = sorted(MIGRATIONS.glob("*.sql"))
    return [f for f in files if f.stem not in applied], applied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true", help="only list the migrations")
    args = parser.parse_args(argv)

    url = read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set: nothing to migrate.", file=sys.stderr)
        return 1
    with psycopg.connect(url, connect_timeout=5) as conn:
        todo, applied = pending(conn)
        conn.commit()
        if args.status:
            for f in sorted(MIGRATIONS.glob("*.sql")):
                print(f"{'applied' if f.stem in applied else 'pending'}  {f.stem}")
            return 0
        for f in todo:
            with conn.transaction():
                conn.execute(f.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (f.stem,))
            print(f"applied  {f.stem}")
    print(f"Database is up to date ({len(applied) + len(todo)} migrations).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
