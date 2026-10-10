"""Show how PostgreSQL runs one of the API's queries: EXPLAIN (ANALYZE, BUFFERS).

    python -m scripts.explain queue                   one team's open tickets, newest first
    python -m scripts.explain queue --team login --status pending
    python -m scripts.explain customer --customer C-3835
    python -m scripts.explain messages --ticket T-399000
    python -m scripts.explain latest-run --ticket T-399000
    python -m scripts.explain queue --json            the plan as JSON (for the explorer)

ANALYZE really runs the query (for a SELECT, nothing changes). Read the plan from the
innermost line outwards: each line is a step, with the rows the planner expected
("rows=") and the rows it found ("actual ... rows="), and the time.
"""

import argparse
import json
import sys

import psycopg

from ticket_api import repository
from ticket_api.config import load_env, read_secret


def query(name: str, args) -> tuple[str, dict]:
    if name == "queue":
        return repository.list_query(status=args.status, team=args.team, limit=args.limit)
    if name == "customer":
        return repository.list_query(customer_id=args.customer, limit=args.limit)
    if name == "messages":
        return (
            "SELECT message_id, author, body, created_at FROM messages"
            " WHERE ticket_id = %(ticket)s ORDER BY created_at, message_id",
            {"ticket": args.ticket},
        )
    if name == "latest-run":
        return (
            "SELECT model, status FROM ai_runs WHERE ticket_id = %(ticket)s"
            " ORDER BY created_at DESC LIMIT 1",
            {"ticket": args.ticket},
        )
    raise SystemExit(f"unknown query {name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", choices=["queue", "customer", "messages", "latest-run"])
    parser.add_argument("--status", default="open")
    parser.add_argument("--team", default="billing")
    parser.add_argument("--customer", default="C-0003")
    parser.add_argument("--ticket", default="T-30002")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true", help="print the plan as JSON")
    parser.add_argument(
        "--no-analyze", action="store_true", help="only the estimate; do not run the query"
    )
    args = parser.parse_args(argv)
    load_env()
    url = read_secret("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 1
    sql, params = query(args.query, args)
    options = "FORMAT JSON" if args.json else "FORMAT TEXT"
    if not args.no_analyze:
        options = "ANALYZE, BUFFERS, " + options
    with psycopg.connect(url) as conn:
        rows = conn.execute(f"EXPLAIN ({options}) {sql}", params).fetchall()
    if args.json:
        print(json.dumps(rows[0][0], indent=2))
    else:
        print("\n".join(r[0] for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
