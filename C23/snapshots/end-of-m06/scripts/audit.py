"""Read the audit events, and check that no secret got into them.

    python -m scripts.audit                       the 20 newest events
    python -m scripts.audit --tenant larkfield --result denied
    python -m scripts.audit --actor usr-kwame
    python -m scripts.audit --check               look for tokens and secrets in every event
    python -m scripts.audit --summary             events by action and result

Events answer "who did what, where, with which result", and "who tried". They never hold
a token, a cookie, a password, a client secret or the text of a message.
"""

import argparse
import json
import os
import re
import sys

import psycopg
from psycopg.rows import dict_row

from ticket_api.config import load_env, read_secret

JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]*")


def secrets_in_env() -> list[str]:
    names = ("OIDC_CLIENT_SECRET", "WORKER_CLIENT_SECRET", "SESSION_KEY", "API_KEY")
    return [v for v in (read_secret(n) for n in names) if v and len(v) >= 8]


def check(conn) -> int:
    known = secrets_in_env()
    bad = 0
    rows = conn.execute("SELECT * FROM audit_events ORDER BY event_id").fetchall()
    for row in rows:
        text = json.dumps(row, default=str)
        found = [
            n
            for n, hit in (
                ("a JWT", JWT.search(text)),
                ("Bearer", "Bearer " in text),
                ("a secret of .env", any(s in text for s in known)),
            )
            if hit
        ]
        if found:
            bad += 1
            print(f"  event {row['event_id']} ({row['action']}) has {', '.join(found)}")
    print(f"Checked {len(rows)} audit events: {bad} with a token or a secret.")
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tenant")
    parser.add_argument("--actor")
    parser.add_argument("--result", choices=["allowed", "denied", "done", "failed"])
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    load_env()
    with psycopg.connect(
        os.environ.get("DATABASE_URL") or read_secret("DATABASE_URL"), row_factory=dict_row
    ) as conn:
        if args.check:
            return 1 if check(conn) else 0
        if args.summary:
            for r in conn.execute(
                "SELECT action, result, count(*) AS n FROM audit_events GROUP BY 1, 2 ORDER BY 1, 2"
            ):
                print(f"  {r['action']:<28} {r['result']:<8} {r['n']:>5}")
            return 0
        rows = conn.execute(
            "SELECT * FROM audit_events WHERE (%(t)s::text IS NULL OR tenant_id = %(t)s)"
            " AND (%(a)s::text IS NULL OR actor_id = %(a)s)"
            " AND (%(r)s::text IS NULL OR result = %(r)s) ORDER BY event_id DESC LIMIT %(n)s",
            {"t": args.tenant, "a": args.actor, "r": args.result, "n": args.limit},
        ).fetchall()
    for r in reversed(rows):
        print(
            f"{r['at']:%H:%M:%S} {r['actor_id'] or '(no identity)':<12} {r['tenant_id'] or '-':<10}"
            f" {r['action']:<24} {r['result']:<7} {r['reason'] or ''}"
            f"{'  ' + r['target'] if r['target'] else ''}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
