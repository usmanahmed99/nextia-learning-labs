"""The application database: only checked results go in."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .validate import Verdict

RESULTS_DB = Path(__file__).resolve().parent.parent / "results.sqlite"


class InvalidResult(Exception):
    """Raised when code tries to save a result that did not pass both gates."""


class ResultStore:
    def __init__(self, path: Path = RESULTS_DB):
        self.path = path
        with sqlite3.connect(self.path) as con:
            con.execute("""CREATE TABLE IF NOT EXISTS results (ticket_id TEXT, team TEXT, needs_human INTEGER,
                order_id TEXT, reply TEXT, prompt TEXT, model TEXT, saved_at TEXT)""")

    def save(self, ticket_id: str, verdict: Verdict, prompt: str, model: str) -> None:
        if not verdict.valid:
            codes = ", ".join(p.code for p in verdict.problems) or "no analysis"
            raise InvalidResult(f"{ticket_id} was not saved: {codes}")
        a = verdict.analysis
        with sqlite3.connect(self.path) as con:
            con.execute("INSERT INTO results VALUES (?,?,?,?,?,?,?,?)",
                        (ticket_id, a.team, int(a.needs_human), a.order.order_id if a.order else None, a.reply,
                         prompt, model, datetime.now(timezone.utc).isoformat(timespec="seconds")))

    def count(self) -> int:
        with sqlite3.connect(self.path) as con:
            return con.execute("SELECT COUNT(*) FROM results").fetchone()[0]
