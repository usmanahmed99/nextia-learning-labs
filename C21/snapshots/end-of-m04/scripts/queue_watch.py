"""Watch the queue: one line per second (Ctrl+C to stop).

    python -m scripts.queue_watch [--seconds 60] [--every 1]

queued = waiting (also for a retry), ready = may run now, running = taken by a worker,
oldest = the age of the oldest queued job, done/min = finished in the last minute.
"""

import argparse
import sys
import time

import psycopg
from psycopg.rows import dict_row

from ticket_api import jobs
from ticket_api.config import load_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--every", type=float, default=1.0)
    args = parser.parse_args(argv)
    url = load_settings().database_url
    started = time.monotonic()
    print(
        f"{'time':>6} {'queued':>7} {'ready':>6} {'running':>8} {'oldest s':>9} {'done/min':>9}"
        f" {'dead':>5}"
    )
    try:
        with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
            while time.monotonic() - started < args.seconds:
                s = jobs.stats(conn)
                print(
                    f"{time.monotonic() - started:>6.0f} {s['queued']:>7} {s['ready']:>6} "
                    f"{s['running']:>8} {s['oldest_queued_seconds']:>9.1f} "
                    f"{s['succeeded_last_minute']:>9} {s['dead_letter']:>5}",
                    flush=True,
                )
                time.sleep(args.every)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
