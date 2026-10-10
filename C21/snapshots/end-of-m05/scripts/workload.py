"""Describe the help desk's workload in numbers, from the tickets in the database.

    python -m scripts.workload                 the loaded data (small or large)
    python -m scripts.workload --factor 10     ... and the same workload ten times bigger

It prints how many tickets arrive per day, per hour and in the busiest minute, how long
the ticket texts are, and what that means for the AI provider: each ticket needs two
chat calls and one embedding call, and the provider allows a fixed number of requests
per minute (its quota). Use the large data for real arrival rates (the small data has
only 200 tickets).
"""

import argparse
import statistics
import sys

import psycopg
from psycopg.rows import tuple_row

from ticket_api.config import load_env, read_secret

CHAT_CALLS_PER_TICKET = 2
QUOTA_RPM = 100  # chat-small's quota, as the provider reported it (requests per minute)
CHARS_PER_TOKEN = 4  # about 4 characters per token for English text


def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(p / 100 * len(s)))]


def describe(conn: psycopg.Connection, factor: float) -> dict:
    # Only the tickets of the practice data: new tickets from the API (and from load tests)
    # start at T-500001.
    cur = conn.cursor(row_factory=tuple_row)
    rows = cur.execute(
        "SELECT created_at, length(subject) + length(body) AS chars FROM tickets"
        " WHERE substring(ticket_id FROM 3)::int < 500000 ORDER BY created_at"
    ).fetchall()
    if not rows:
        raise SystemExit("No tickets in the database: python -m scripts.load first.")
    first, last = rows[0][0], rows[-1][0]
    per_day, per_hour, per_minute = {}, {}, {}
    for created, _ in rows:
        for bucket, key in (
            (per_day, created.date()),
            (per_hour, created.replace(minute=0, second=0)),
            (per_minute, created.replace(second=0)),
        ):
            bucket[key] = bucket.get(key, 0) + 1
    days = (last.date() - first.date()).days + 1
    hours_open = [n for n in per_hour.values()]
    chars = [c for _, c in rows]
    busiest_hour = max(per_hour.values())
    return {
        "tickets": len(rows),
        "first": first.date().isoformat(),
        "last": last.date().isoformat(),
        "days": days,
        "per_day_mean": len(rows) / days,
        "per_day_max": max(per_day.values()),
        "per_open_hour_mean": statistics.fmean(hours_open),
        "busiest_hour": busiest_hour,
        "busiest_minute": max(per_minute.values()),
        "chars_median": statistics.median(chars),
        "chars_p95": pct(chars, 95),
        "chars_max": max(chars),
        "factor": factor,
        "peak_per_second": busiest_hour * factor / 3600,
        "chat_calls_per_minute": busiest_hour * factor / 60 * CHAT_CALLS_PER_TICKET,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--factor", type=float, default=1.0, help="multiply the arrivals (e.g. 10)")
    args = parser.parse_args(argv)
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL")) as conn:
        w = describe(conn, args.factor)
    print(f"Tickets: {w['tickets']:,} from {w['first']} to {w['last']} ({w['days']} days)")
    print(f"Per day: {w['per_day_mean']:,.0f} on average, {w['per_day_max']:,} on the busiest day")
    print(
        f"Per hour with tickets: {w['per_open_hour_mean']:,.1f} on average, "
        f"{w['busiest_hour']:,} in the busiest hour"
    )
    print(f"Busiest minute: {w['busiest_minute']} tickets")
    print(
        f"Ticket text (subject + body): median {w['chars_median']:,.0f} characters "
        f"(about {w['chars_median'] / CHARS_PER_TOKEN:,.0f} tokens), p95 {w['chars_p95']:,}, "
        f"longest {w['chars_max']:,}"
    )
    label = "" if w["factor"] == 1 else f" x {w['factor']:g}"
    print(
        f"Busiest hour{label}: {w['busiest_hour'] * w['factor']:,.0f} tickets = "
        f"{w['peak_per_second']:.2f} per second on average"
    )
    print(
        f"Chat calls to the AI provider in that hour: {w['chat_calls_per_minute']:,.0f} per minute "
        f"(the quota is {QUOTA_RPM} per minute)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
