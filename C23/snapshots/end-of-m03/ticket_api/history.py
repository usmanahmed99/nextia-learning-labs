"""Keep a record of the classifications in PostgreSQL.

The record has the result of each classification, never the ticket's text.
History is optional: without DATABASE_URL the API classifies tickets and
keeps no record. The table is made by the migrations in migrations/
(python -m ticket_api.migrate), not by the app. The connections come from the
app's pool (ticket_api/db.py).
"""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from ticket_api.db import Database, DatabaseBusy, DatabaseUnavailable


class HistoryUnavailable(Exception):
    """History is off, or the database does not answer."""


class History:
    def __init__(self, db: Database):
        self.db = db

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        try:
            with self.db.connection() as conn:
                yield conn
        except (DatabaseUnavailable, DatabaseBusy) as error:
            raise HistoryUnavailable(str(error)) from error

    def check(self) -> None:
        with self.connect() as conn:
            conn.execute("SELECT 1")

    def add(self, request_id: str, result: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO classifications"
                " (request_id, category, priority, confidence, score, model_version)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    request_id,
                    result["category"],
                    result["priority"],
                    result["confidence"],
                    result["score"],
                    result["model_version"],
                ),
            )

    def recent(self, limit: int) -> list[dict]:
        with self.connect() as conn:
            return conn.execute(
                # Rows from version 1.1.0 have no score: use confidence.
                "SELECT request_id, category, priority, confidence,"
                " COALESCE(score, confidence) AS score, model_version, created_at"
                " FROM classifications ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
