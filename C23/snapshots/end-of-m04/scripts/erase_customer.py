"""Delete a customer's data everywhere: database rows, files and vectors.

    python -m scripts.erase_customer C-0012 --dry-run        what would be deleted
    python -m scripts.erase_customer C-0012                  delete it
    python -m scripts.erase_customer --finish                delete the files that are still waiting
    python -m scripts.erase_customer C-0012 --crash-after-database   a constructed failure

Step 1, one database transaction: delete the customer's tickets, messages,
attachment rows and vectors, remove the text of their AI runs (the cost records
stay, with no ticket), delete the customer, write the keys of their files into
file_deletions (the outbox), and write a record in erasures (counts only).
Step 2, after the commit: delete each file in the object storage, and mark its
row in file_deletions as done.

If step 2 does not finish (a crash, a network error), the keys are still in
file_deletions: `--finish` (or `python -m scripts.scan --fix`) deletes them later.
`--crash-after-database` stops the program between step 1 and step 2 on purpose.
Backups still have the data until they expire: keep backups only as long as the
retention plan says.
"""

import argparse
import sys

import psycopg
from psycopg.rows import dict_row

from ticket_api.config import load_env, load_settings, read_secret
from ticket_api.files import make_store


def plan(conn: psycopg.Connection, customer_id: str) -> dict:
    q = lambda sql: conn.execute(sql, {"c": customer_id}).fetchone()["n"]  # noqa: E731
    return {
        "tickets": q("SELECT count(*) AS n FROM tickets WHERE customer_id = %(c)s"),
        "messages": q(
            "SELECT count(*) AS n FROM messages m JOIN tickets t USING (ticket_id) WHERE"
            " t.customer_id = %(c)s"
        ),
        "files": q(
            "SELECT count(*) AS n FROM attachments a JOIN tickets t USING (ticket_id) WHERE"
            " t.customer_id = %(c)s"
        ),
        "vectors": q(
            "SELECT count(*) AS n FROM ticket_embeddings e JOIN tickets t USING (ticket_id)"
            " WHERE t.customer_id = %(c)s"
        ),
        "ai_runs": q(
            "SELECT count(*) AS n FROM ai_runs r JOIN tickets t USING (ticket_id) WHERE"
            " t.customer_id = %(c)s"
        ),
    }


def erase_in_database(conn: psycopg.Connection, customer_id: str) -> dict:
    with conn.transaction():
        if (
            conn.execute(
                "SELECT 1 FROM customers WHERE customer_id = %s FOR UPDATE", (customer_id,)
            ).fetchone()
            is None
        ):
            raise SystemExit(f"Customer {customer_id} does not exist.")
        counts = plan(conn, customer_id)
        tickets = "SELECT ticket_id FROM tickets WHERE customer_id = %(c)s"
        p = {"c": customer_id}
        conn.execute(
            "INSERT INTO file_deletions (object_key, reason) SELECT object_key, 'erasure ' || %(c)s"
            f" FROM attachments WHERE ticket_id IN ({tickets})"
            # A key that was deleted before (a restored backup brought its file back) waits again.
            " ON CONFLICT (object_key) DO UPDATE SET deleted_at = NULL, requested_at = now()",
            p,
        )
        conn.execute(f"DELETE FROM attachments WHERE ticket_id IN ({tickets})", p)
        # AI runs keep their cost, with no ticket and no text.
        conn.execute(
            f"UPDATE ai_runs SET output = NULL, ticket_id = NULL WHERE ticket_id IN ({tickets})", p
        )
        # Vectors and messages go with their tickets (ON DELETE CASCADE).
        conn.execute("DELETE FROM tickets WHERE customer_id = %(c)s", p)
        conn.execute("DELETE FROM customers WHERE customer_id = %(c)s", p)
        conn.execute(
            "INSERT INTO erasures (customer_id, tickets, messages, files, vectors, ai_runs)"
            " VALUES (%(c)s, %(tickets)s, %(messages)s, %(files)s, %(vectors)s, %(ai_runs)s)",
            {**p, **counts},
        )
    return counts


def finish(conn: psycopg.Connection, store) -> tuple[int, int]:
    """Delete the files that file_deletions still lists; mark each one done."""
    keys = [
        r["object_key"]
        for r in conn.execute(
            "SELECT object_key FROM file_deletions WHERE deleted_at IS NULL ORDER BY"
            " requested_at, object_key"
        )
    ]
    deleted = 0
    for key in keys:
        if store.delete(key):
            deleted += 1
        # Deleting a file that is already gone is fine: the goal is that it does not exist.
        conn.execute("UPDATE file_deletions SET deleted_at = now() WHERE object_key = %s", (key,))
        conn.commit()
    return len(keys), deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("customer_id", nargs="?")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--finish", action="store_true", help="only delete the files that are waiting"
    )
    parser.add_argument("--crash-after-database", action="store_true", help="a constructed failure")
    args = parser.parse_args(argv)
    load_env()
    store = make_store(load_settings())
    with psycopg.connect(read_secret("DATABASE_URL"), row_factory=dict_row) as conn:
        if args.finish:
            if store is None:
                print("STORAGE_CONNECTION_STRING is not set.", file=sys.stderr)
                return 1
            n, deleted = finish(conn, store)
            print(f"Files waiting: {n}. Deleted now: {deleted}; already gone: {n - deleted}.")
            return 0
        if not args.customer_id:
            parser.error("give a customer ID, or --finish")
        if args.dry_run:
            counts = plan(conn, args.customer_id)
            print(f"{args.customer_id} has: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
            return 0
        counts = erase_in_database(conn, args.customer_id)
        print(
            f"Database: deleted {counts['tickets']} tickets, {counts['messages']} messages,"
            f" {counts['files']} attachment rows, {counts['vectors']} vectors; removed the text of"
            f" {counts['ai_runs']} AI runs (their cost stays). {counts['files']} files are"
            " waiting in file_deletions."
        )
        if args.crash_after_database:
            print("Stopped on purpose before the files were deleted (--crash-after-database).")
            return 1
        if store is None:
            print("STORAGE_CONNECTION_STRING is not set: the files wait in file_deletions.")
            return 0
        n, deleted = finish(conn, store)
        print(f"Object storage: deleted {deleted} of {n} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
