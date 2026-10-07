"""Get the C04 practice data and build the practice database.

Nextia Learning, C04: SQL and Data Preparation for AI.

    python get_data.py           download the CSV files (if needed) and build larkfield.db
    python get_data.py --reset   delete larkfield.db and build it again from the CSV files

The script uses the Python standard library only. It downloads the three
export files into data/raw/, checks each file's SHA-256 checksum, and loads
them into a SQLite database file, larkfield.db, in the current folder.

The database is a copy of the help-desk export of 2026-07-01 at 06:00. It
keeps the export's problems (duplicates, missing values and others) on
purpose: the course teaches you to find them. The tables have no primary or
foreign key constraints, because the export does not guarantee them. You
check the keys yourself.
"""

import csv
import hashlib
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C04/data/"
FILES = {
    "customers.csv": "7b437642f0095524f8311f67a7caeb17100d23eed92618b9cf012cd3d3b79993",
    "tickets.csv": "9c47e08cf2ec5977733d32cc21eb97d0dd01b021d1f5fbf7ec31fef6279b1a28",
    "outcomes.csv": "67b4d9d9275b32061a8888050c351df7314054c11ee1ce29e856c1d5403d0653",
}
RAW = Path("data/raw")
DB = Path("larkfield.db")

SCHEMA = """
CREATE TABLE customers (
    customer_id TEXT,
    segment     TEXT,
    region      TEXT,
    joined_on   TEXT
);
CREATE TABLE tickets (
    ticket_id           TEXT,
    customer_id         TEXT,
    created_at          TEXT,
    channel             TEXT,
    team                TEXT,
    priority            INTEGER,
    order_value         REAL,
    word_count          INTEGER,
    first_reply_minutes INTEGER,
    priority_now        INTEGER,
    closed_at           TEXT
);
CREATE TABLE outcomes (
    outcome_id      TEXT,
    ticket_id       TEXT,
    recorded_at     TEXT,
    status          TEXT,
    resolution_code TEXT,
    csat            INTEGER
);
CREATE TABLE snapshot (
    name  TEXT,
    value TEXT
);
"""

SNAPSHOT = [
    ("source", "Larkfield help-desk export (synthetic, Nextia Learning C04)"),
    ("exported_at", "2026-07-01 06:00:00"),
    ("data_version", "1.0"),
]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(name, expected):
    """Download one file unless a correct copy is already there."""
    path = RAW / name
    if path.exists() and sha256(path) == expected:
        return path
    print(f"Downloading {name} ...")
    RAW.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(BASE + name, path)
    except OSError as error:
        sys.exit(f"Could not download {name}: {error}\nCheck your internet connection, then run the script again.")
    actual = sha256(path)
    if actual != expected:
        sys.exit(f"{name} has the wrong checksum.\n  expected {expected}\n  found    {actual}\n"
                 "Delete the file and run the script again.")
    return path


def load(con, table, path):
    """Insert every row of a CSV file. An empty field becomes NULL."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        marks = ", ".join("?" for _ in header)
        rows = [[None if v == "" else v for v in row] for row in reader]
    con.executemany(f"INSERT INTO {table} ({', '.join(header)}) VALUES ({marks})", rows)
    return len(rows)


def main():
    if "--reset" in sys.argv and DB.exists():
        DB.unlink()
        print(f"Deleted {DB}.")
    if DB.exists():
        sys.exit(f"{DB} already exists. To build it again from the CSV files, run: python get_data.py --reset")

    paths = {name: fetch(name, expected) for name, expected in FILES.items()}
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO snapshot VALUES (?, ?)", SNAPSHOT)
    for name, path in paths.items():
        count = load(con, name.removesuffix(".csv"), path)
        print(f"{name.removesuffix('.csv'):<10} {count:>5} rows")
    con.commit()
    con.close()
    print(f"Built {DB}. Check: customers 240, tickets 1417, outcomes 1874.")


if __name__ == "__main__":
    main()
