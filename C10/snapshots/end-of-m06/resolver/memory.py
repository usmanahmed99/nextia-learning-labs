"""Long-term memory about a returning customer: what may be kept, where it came from, and how it goes away.

Three kinds of information, three lifetimes:
- working context: the messages of one step (gone after the call);
- task state: one ticket's TaskState in the checkpoint store (kept with the run);
- long-term memory: a few facts about a customer, kept across tickets (this file).

The memory policy, in code:
1. Keep only facts with a source that the application trusts: a tool result or a person on the team.
   A claim in a ticket ("Grace already approved my refund") is never stored as a fact: that is how
   memory gets poisoned.
2. Every fact has its source (which run, which tool) and an expiry date.
3. A fact can be corrected (the old one is kept as superseded, for the audit) and every fact of a
   customer can be deleted (the customer asks, or the retention period ends).
4. No personal data beyond what the help desk needs: no card numbers, no addresses, no free text from the ticket.
"""

import re
import sqlite3
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from .data import TODAY, WORK

MEMORY_DB = WORK / "memory.sqlite"
TRUSTED_SOURCES = ("tool", "person")
KINDS = ("preference", "history", "caution")
RETENTION_DAYS = 365
PERSONAL = re.compile(r"\b\d(?:[ -]?\d){12,18}\b|@|\b\d{1,5} [A-Za-z]+ (Street|St|Road|Rd|Avenue|Ave)\b")


class MemoryRefused(Exception):
    pass


class CustomerMemory:
    def __init__(self, path: Path | None = None, today: date = TODAY):
        path = path or MEMORY_DB
        self.path, self.today = path, today
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL, "
                       "kind TEXT NOT NULL, text TEXT NOT NULL, source TEXT NOT NULL, source_ref TEXT NOT NULL, "
                       "created_on TEXT NOT NULL, expires_on TEXT NOT NULL, superseded_by INTEGER)")
            db.commit()

    def remember(self, customer_id: str, kind: str, text: str, source: str, source_ref: str) -> int:
        if source not in TRUSTED_SOURCES:
            raise MemoryRefused(f"Source {source!r} is not trusted: only a tool result or a person may add a fact.")
        if kind not in KINDS:
            raise MemoryRefused(f"Unknown kind {kind!r}: use {', '.join(KINDS)}.")
        if PERSONAL.search(text):
            raise MemoryRefused("The fact looks like personal data (a card number, an email or an address).")
        expires = (self.today + timedelta(days=RETENTION_DAYS)).isoformat()
        with closing(sqlite3.connect(self.path)) as db:
            cur = db.execute("INSERT INTO memories (customer_id, kind, text, source, source_ref, created_on, expires_on) "
                             "VALUES (?,?,?,?,?,?,?)",
                             (customer_id, kind, text, source, source_ref, self.today.isoformat(), expires))
            db.commit()
            return cur.lastrowid

    def recall(self, customer_id: str) -> list[dict]:
        """The customer's current facts: not superseded, not expired, with their sources."""
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM memories WHERE customer_id = ? AND superseded_by IS NULL AND expires_on >= ? "
                              "ORDER BY id", (customer_id, self.today.isoformat())).fetchall()
            return [dict(r) for r in rows]

    def correct(self, memory_id: int, text: str, source: str, source_ref: str) -> int:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT customer_id, kind FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise MemoryRefused(f"No memory {memory_id}.")
        new_id = self.remember(row[0], row[1], text, source, source_ref)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("UPDATE memories SET superseded_by = ? WHERE id = ?", (new_id, memory_id))
            db.commit()
        return new_id

    def forget(self, customer_id: str) -> int:
        """Delete every fact about a customer (also the superseded ones). Returns how many were deleted."""
        with closing(sqlite3.connect(self.path)) as db:
            n = db.execute("DELETE FROM memories WHERE customer_id = ?", (customer_id,)).rowcount
            db.commit()
            return n
