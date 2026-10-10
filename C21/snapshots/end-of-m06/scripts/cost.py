"""Estimated cost per ticket of the AI work, from the recorded tokens and the dated prices.

    python -m scripts.cost [--since-minutes 60] [--compute-usd-per-hour 0.05 --hours 1]

It reads ai_runs of the tickets that came through the API (T-500001 and later): tokens in
and out per call, times the prices in ticket_api/prices.py (checked on PRICES_CHECKED).
With --compute-usd-per-hour it adds the cost of the machines that ran for --hours, shared
by the tickets of that time. The simulated provider counts tokens like the real one did in
the recordings; the money is an estimate, not a bill.
"""

import argparse
import sys

import psycopg
from psycopg.rows import dict_row

from ticket_api.config import load_settings
from ticket_api.prices import PRICES, PRICES_CHECKED


def per_ticket(conn: psycopg.Connection, since_minutes: float | None) -> dict:
    where = "substring(r.ticket_id FROM 3)::int >= 500000 AND r.status = 'ok'"
    params: dict = {}
    if since_minutes:
        where += " AND r.created_at > now() - make_interval(mins => %(m)s)"
        params["m"] = since_minutes
    rows = conn.execute(
        "SELECT r.task, regexp_replace(r.model, ' \\(simulated\\)$', '') AS model,"
        " count(DISTINCT r.ticket_id) AS tickets, count(*) AS calls,"
        " sum(r.tokens_in) AS tokens_in, sum(r.tokens_out) AS tokens_out"
        f" FROM ai_runs r WHERE {where} GROUP BY 1, 2 ORDER BY 1",
        params,
    ).fetchall()
    tickets = conn.execute(
        f"SELECT count(DISTINCT r.ticket_id) AS n FROM ai_runs r WHERE {where}", params
    ).fetchone()["n"]
    total = 0.0
    for r in rows:
        p_in, p_out = PRICES.get(r["model"], (0.0, 0.0))
        r["usd"] = (r["tokens_in"] * p_in + r["tokens_out"] * p_out) / 1e6
        total += r["usd"]
    return {"tickets": tickets, "tasks": rows, "ai_usd": total}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since-minutes", type=float)
    parser.add_argument("--compute-usd-per-hour", type=float, default=0.0)
    parser.add_argument("--hours", type=float, default=0.0)
    args = parser.parse_args(argv)
    with psycopg.connect(load_settings().database_url, row_factory=dict_row) as conn:
        c = per_ticket(conn, args.since_minutes)
    if not c["tickets"]:
        print("No AI work yet for tickets from the API (T-500001 and later).")
        return 0
    print(f"Prices checked on {PRICES_CHECKED} (ticket_api/prices.py). Tickets: {c['tickets']}")
    for r in c["tasks"]:
        print(
            f"  {r['task']:<12} {r['model']:<12} {r['calls']:>6} calls  {r['tokens_in']:>8} in"
            f"  {r['tokens_out']:>7} out  US${r['usd']:.6f}"
        )
    per = c["ai_usd"] / c["tickets"]
    print(f"AI cost per ticket: US${per:.7f} (US${per * 1000:.4f} per 1,000 tickets)")
    if args.compute_usd_per_hour and args.hours:
        compute = args.compute_usd_per_hour * args.hours / c["tickets"]
        print(
            f"Compute per ticket: US${compute:.7f} ({args.compute_usd_per_hour} US$/h for "
            f"{args.hours} h); total US${per + compute:.7f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
