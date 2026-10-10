"""Print the access matrix: what each role may do, and what each person may do in each shop.

    python -m scripts.access_matrix                 roles x actions, then people x shops
    python -m scripts.access_matrix --user usr-camille
    python -m scripts.access_matrix --json          every decision, for the course's explorer

The roles come from ticket_api/access.py; the memberships come from the database
(python -m scripts.load first). Nothing is changed.
"""

import argparse
import json
import sys

import psycopg
from psycopg.rows import dict_row

from ticket_api.access import ACTIONS, ROLES, decide
from ticket_api.config import load_env, read_secret

MARK = {200: "yes", 403: "403", 404: "404"}


def people(conn: psycopg.Connection) -> tuple[list[dict], list[str], dict]:
    users = conn.execute("SELECT user_id, name FROM users ORDER BY user_id").fetchall()
    tenants = [r["tenant_id"] for r in conn.execute("SELECT tenant_id FROM tenants ORDER BY 1")]
    roles = {
        (r["user_id"], r["tenant_id"]): r["role"]
        for r in conn.execute("SELECT user_id, tenant_id, role FROM memberships")
    }
    return users, tenants, roles


def decisions(conn: psycopg.Connection) -> dict:
    users, tenants, roles = people(conn)
    out = []
    for u in users:
        for t in tenants:
            role = roles.get((u["user_id"], t))
            for action in ACTIONS:
                d = decide(role, action)
                out.append(
                    {
                        "user": u["user_id"],
                        "name": u["name"],
                        "tenant": t,
                        "role": role,
                        "action": action,
                        "allowed": d.allowed,
                        "status": d.status,
                        "code": d.code,
                        "rule": d.rule,
                    }
                )
    return {"roles": list(ROLES), "actions": list(ACTIONS), "tenants": tenants, "decisions": out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", help="only this person, for example usr-camille")
    parser.add_argument("--json", action="store_true", help="print every decision as JSON")
    args = parser.parse_args(argv)
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL"), row_factory=dict_row) as conn:
        result = decisions(conn)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if not args.user:
        print("What each role may do (yes = allowed):")
        print(f"  {'action':<20}" + "".join(f"{r:>11}" for r in ROLES))
        for action in ACTIONS:
            cells = "".join(f"{MARK[decide(r, action).status]:>11}" for r in ROLES)
            print(f"  {action:<20}{cells}")
        print()
    rows = [d for d in result["decisions"] if not args.user or d["user"] == args.user]
    if not rows:
        print(f"No person with the ID {args.user}.", file=sys.stderr)
        return 1
    print("What each person may do in each shop (404 = not a member: the API shows nothing):")
    seen = []
    for d in rows:
        key = (d["user"], d["tenant"])
        if key in seen:
            continue
        seen.append(key)
        mine = [r for r in rows if (r["user"], r["tenant"]) == key]
        allowed = [r["action"] for r in mine if r["allowed"]]
        role = d["role"] or "no membership"
        what = ", ".join(allowed) if allowed else "nothing"
        print(f"  {d['name']:<8} at {d['tenant']:<10} {role:<14} {what}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
