"""Row-level security, step by step: who sees how many tickets (migrations/017).

    python -m scripts.rls_demo

Every query below forgets "WHERE tenant_id = ..." on purpose (constructed for the course).
Read-only, except the last step, which tries an insert and is refused.
"""

import sys

import psycopg

from ticket_api.config import load_env, read_secret

COUNT = "SELECT count(*) FROM tickets"


def step(conn, text: str, *setup: str) -> None:
    with conn.transaction():
        for sql in setup:
            conn.execute(sql)
        user = conn.execute("SELECT current_user").fetchone()[0]
        tenant = conn.execute("SELECT current_setting('app.tenant_id', true)").fetchone()[0]
        n = conn.execute(COUNT).fetchone()[0]
        print(
            f"  {text:<52} user {user:<10} app.tenant_id {tenant or '(empty)':<10} -> {n} tickets"
        )
        raise psycopg.Rollback()  # change nothing


def main() -> int:
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL")) as conn:
        print(f"{COUNT};")
        step(conn, "1. as the Compose user, no organization")
        step(
            conn,
            "2. as the Compose user, organization bramble",
            "SELECT set_config('app.tenant_id', 'bramble', true)",
        )
        step(conn, "3. as ticket_app, no organization", "SET LOCAL ROLE ticket_app")
        step(
            conn,
            "4. as ticket_app, organization bramble",
            "SET LOCAL ROLE ticket_app",
            "SELECT set_config('app.tenant_id', 'bramble', true)",
        )
        print("  5. as ticket_app for bramble, insert a message for Larkfield's T-30002:")
        try:
            with conn.transaction():
                conn.execute("SET LOCAL ROLE ticket_app")
                conn.execute("SELECT set_config('app.tenant_id', 'bramble', true)")
                conn.execute(
                    "INSERT INTO messages (tenant_id, ticket_id, author, body)"
                    " VALUES ('larkfield', 'T-30002', 'agent', 'x')"
                )
        except psycopg.Error as error:
            print(f"     {type(error).__name__}: {str(error).strip().splitlines()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
