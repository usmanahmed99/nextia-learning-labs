"""Find where the database, the object storage and the vectors disagree.

    python -m scripts.scan            report only
    python -m scripts.scan --fix      also delete the files that file_deletions lists
    python -m scripts.scan --json     the report as JSON

It looks for:
  orphan files        files in object storage that no attachment row and no pending deletion knows
  missing files       attachment rows marked "stored" whose file is not in object storage
  waiting deletions   rows in file_deletions that are not done (a deletion stopped halfway)
  old pending uploads uploads that started more than a day ago and never finished
  stale vectors       vectors made from a ticket text that has changed since (checksum differs)
  vectors of other embedding versions (kept until a person deletes them)
  tickets with no vector of the current embedding version

It changes nothing unless you give --fix, and --fix only finishes waiting deletions:
a person decides about the rest.
"""

import argparse
import json
import sys

import psycopg
from psycopg.rows import dict_row

from scripts.erase_customer import finish
from ticket_api.config import load_env, load_settings, read_secret
from ticket_api.files import make_store

TEXT_SHA = "encode(sha256(convert_to(t.subject || E'\\n' || t.body, 'UTF8')), 'hex')"


def scan(conn: psycopg.Connection, store) -> dict:
    report = {}
    rows = conn.execute("SELECT object_key, status FROM attachments").fetchall()
    known = {r["object_key"] for r in rows}
    stored = {r["object_key"] for r in rows if r["status"] == "stored"}
    waiting = {
        r["object_key"]
        for r in conn.execute("SELECT object_key FROM file_deletions WHERE deleted_at IS NULL")
    }
    if store is not None:
        present = set(store.keys("tickets/"))
        report["orphan_files"] = sorted(present - known - waiting)
        report["missing_files"] = sorted(stored - present)
        report["waiting_deletions"] = sorted(waiting & present)
        report["waiting_deletions_already_gone"] = sorted(waiting - present)
    else:
        report["object_storage"] = "not set up (STORAGE_CONNECTION_STRING): file checks skipped"
        report["waiting_deletions"] = sorted(waiting)
    report["old_pending_uploads"] = [
        str(r["attachment_id"])
        for r in conn.execute(
            "SELECT attachment_id FROM attachments WHERE status = 'pending' AND created_at <"
            " now() - interval '1 day'"
        )
    ]
    version = conn.execute("SELECT version FROM embedding_versions WHERE is_current").fetchone()
    version = version["version"] if version else None
    report["embedding_version"] = version
    report["stale_vectors"] = [
        r["ticket_id"]
        for r in conn.execute(
            f"SELECT e.ticket_id FROM ticket_embeddings e JOIN tickets t USING (ticket_id)"
            f" WHERE e.source_sha256 <> {TEXT_SHA} ORDER BY 1"
        )
    ]
    report["vectors_of_other_versions"] = conn.execute(
        "SELECT count(*) AS n FROM ticket_embeddings WHERE embedding_version <> %s", (version,)
    ).fetchone()["n"]
    report["tickets_without_current_vector"] = conn.execute(
        "SELECT count(*) AS n FROM tickets t WHERE NOT EXISTS (SELECT 1 FROM ticket_embeddings e"
        " WHERE e.ticket_id = t.ticket_id AND e.embedding_version = %s)",
        (version,),
    ).fetchone()["n"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="finish the waiting file deletions")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    load_env()
    store = make_store(load_settings())
    with psycopg.connect(read_secret("DATABASE_URL"), row_factory=dict_row) as conn:
        report = scan(conn, store)
        if (
            args.fix
            and store is not None
            and report["waiting_deletions"] + report["waiting_deletions_already_gone"]
        ):
            n, deleted = finish(conn, store)
            report["fixed"] = f"finished {n} waiting deletions ({deleted} files deleted)"
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    for key, value in report.items():
        if isinstance(value, list):
            shown = ", ".join(value[:3]) + (" ..." if len(value) > 3 else "")
            print(f"{key.replace('_', ' '):<32} {len(value):>6}" + (f"   {shown}" if value else ""))
        else:
            print(f"{key.replace('_', ' '):<32} {value!s:>6}")
    problems = sum(
        len(report.get(k, []))
        for k in (
            "orphan_files",
            "missing_files",
            "waiting_deletions",
            "old_pending_uploads",
            "stale_vectors",
        )
    )
    return 1 if problems and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
