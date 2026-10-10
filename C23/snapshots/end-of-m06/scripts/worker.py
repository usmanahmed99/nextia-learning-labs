"""Run the background jobs: exports, and the deletion of an organization.

    python -m scripts.worker            run queued jobs every 2 seconds (Ctrl+C stops it)
    python -m scripts.worker --once     run the queued jobs once, then stop

Each job runs as the person who asked for it, in their organization: the worker checks
their membership again before it starts (ticket_api/worker.py).
"""

import argparse
import logging
import sys
import time

from ticket_api.config import load_settings
from ticket_api.db import Database
from ticket_api.files import make_store
from ticket_api.worker import run_once


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING)
    settings = load_settings()
    db = Database(settings.database_url, pool=False, row_security=settings.db_row_security)
    files = make_store(settings)
    try:
        while True:
            for job_id, outcome in run_once(db, files):
                with db.connection() as conn:
                    job = conn.execute(
                        "SELECT kind, actor_id, tenant_id, reason, result FROM jobs"
                        " WHERE job_id = %s",
                        (job_id,),
                    ).fetchone()
                print(
                    f"{job_id}  {job['kind']} for {job['actor_id']} in {job['tenant_id']}:"
                    f" {outcome}"
                    + (f" ({job['reason']})" if job["reason"] else "")
                    + (f" {job['result']}" if outcome == "done" else "")
                )
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
