"""Extract tickets and outcomes from larkfield.db into CSV files, with a manifest."""

import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("data/extract")


def run(con, query_file, params, out_file):
    sql = Path(query_file).read_text(encoding="utf-8")
    cursor = con.execute(sql, params)
    header = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return {"query": query_file, "query_sha256": hashlib.sha256(sql.encode()).hexdigest(),
            "file": str(out_file), "rows": len(rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--created-from", default="2026-01-01")
    parser.add_argument("--created-before", default="2026-07-01")
    args = parser.parse_args()
    params = {"created_from": args.created_from, "created_before": args.created_before}

    con = sqlite3.connect("file:larkfield.db?mode=ro", uri=True)
    snapshot = dict(con.execute("SELECT name, value FROM snapshot").fetchall())
    total = con.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    OUT.mkdir(parents=True, exist_ok=True)
    files = [
        run(con, "queries/extract_tickets.sql", params, OUT / "tickets.csv"),
        run(con, "queries/extract_outcomes.sql", params, OUT / "outcomes.csv"),
    ]
    con.close()

    manifest = {
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": snapshot,
        "selection": {**params, "rule": "created_from <= created_at < created_before"},
        "ticket_rows_in_source": total,
        "ticket_rows_not_selected": total - files[0]["rows"],
        "files": files,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for f in files:
        print(f"{f['file']}: {f['rows']} rows")
    print(f"Not selected: {manifest['ticket_rows_not_selected']} ticket row(s)")


if __name__ == "__main__":
    main()
