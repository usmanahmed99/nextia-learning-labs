"""Check the raw export files before anything loads them: each file must have
the expected columns, and each value must be readable as its column's type.

    python scripts/check_input.py
    python scripts/check_input.py --tickets data/raw/tickets-2026-08-01.csv

This check looks at the shape of the data only. Messy values (spellings,
duplicates, sentinels) are the cleaning step's job. Exit code 1 on failure.
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

# The schema of the export of 2026-07-01: column name -> type.
SCHEMAS = {
    "customers": {"customer_id": "text", "segment": "text", "region": "text", "joined_on": "date"},
    "tickets": {
        "ticket_id": "text", "customer_id": "text", "created_at": "datetime", "channel": "text",
        "team": "text", "priority": "integer", "order_value": "number", "word_count": "integer",
        "first_reply_minutes": "integer", "priority_now": "integer", "closed_at": "datetime",
    },
    "outcomes": {
        "outcome_id": "text", "ticket_id": "text", "recorded_at": "datetime", "status": "text",
        "resolution_code": "text", "csat": "integer",
    },
}

# Each type has a function that raises ValueError for a value it cannot read.
READERS = {
    "text": str,
    "integer": int,
    "number": float,
    "date": lambda v: datetime.strptime(v, "%Y-%m-%d"),
    "datetime": lambda v: datetime.strptime(v, "%Y-%m-%d %H:%M:%S"),
}


def check_file(path, schema):
    """Return a list of problems. An empty list means the file is OK."""
    if not path.exists():
        return [f"file not found: {path}"]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = list(reader)

    problems = []
    missing = [c for c in schema if c not in header]
    extra = [c for c in header if c not in schema]
    for column in missing:
        problems.append(f"missing column: {column}")
    for column in extra:
        hint = " (was a column renamed?)" if missing else ""
        problems.append(f"unexpected column: {column}{hint}")

    # An empty value is a missing value. It is allowed here; only values that
    # are present must have the right type.
    for column, kind in schema.items():
        if column not in header or kind == "text":
            continue
        i = header.index(column)
        bad = []
        for line, row in enumerate(rows, start=2):  # line 1 is the header
            value = row[i]
            if value == "":
                continue
            try:
                READERS[kind](value)
            except ValueError:
                bad.append((line, value))
        if bad:
            line, value = bad[0]
            present = sum(1 for row in rows if row[i] != "")
            problems.append(f"{column}: {len(bad)} of {present} values are not a valid {kind}"
                            f" (first: line {line}, {value!r})")
    return problems


def main():
    parser = argparse.ArgumentParser()
    for name in SCHEMAS:
        parser.add_argument(f"--{name}", default=f"data/raw/{name}.csv", type=Path)
    args = parser.parse_args()

    failed = False
    for name, schema in SCHEMAS.items():
        path = getattr(args, name)
        problems = check_file(path, schema)
        print(f"{'PASS' if not problems else 'FAIL'}  {path}")
        for problem in problems:
            print(f"      {problem}")
        failed = failed or bool(problems)

    if failed:
        print("The input does not match the expected schema. Do not load it.")
        sys.exit(1)
    print("The input matches the expected schema.")


if __name__ == "__main__":
    main()
