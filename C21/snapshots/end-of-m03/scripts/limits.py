"""Add up the limits of every process: connections to the database, calls to the provider.

    python -m scripts.limits [--processes 4]

Settings such as DB_POOL_MAX are per process. Four processes with a pool of 10 can open 40
connections; the database accepts max_connections in total (for everyone). The provider's
quota is per account, not per process: more processes do not make it bigger.
"""

import argparse
import sys

import psycopg

from scripts.workload import QUOTA_RPM
from ticket_api.config import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--processes", type=int, default=1, help="API processes (or workers)")
    args = parser.parse_args(argv)
    s = load_settings()
    with psycopg.connect(s.database_url) as conn:
        max_conn = int(conn.execute("SHOW max_connections").fetchone()[0])
        reserved = int(conn.execute("SHOW superuser_reserved_connections").fetchone()[0])
        in_use = conn.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend'"
        ).fetchone()[0]
    planned = args.processes * s.db_pool_max
    print(
        f"Database: max_connections {max_conn} ({reserved} kept for administrators); "
        f"{in_use} in use now"
    )
    print(
        f"API: {args.processes} process(es) x DB_POOL_MAX {s.db_pool_max} = up to {planned} "
        f"connections"
        + ("  <- more than the database allows" if planned > max_conn - reserved else "")
    )
    per = s.provider_max_concurrency or "no limit"
    print(
        f"Provider: PROVIDER_MAX_CONCURRENCY {per} per process; the quota is {QUOTA_RPM} chat "
        f"requests per minute for the whole account, whatever the number of processes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
