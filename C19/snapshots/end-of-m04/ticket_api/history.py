"""Keep a record of the classifications in PostgreSQL.

The record has the result of each classification, never the ticket's text.
History is optional: without DATABASE_URL the API classifies tickets and
keeps no record. The table is made by the migrations in migrations/
(python -m ticket_api.migrate), not by the app.
"""

import psycopg
from psycopg.rows import dict_row


class HistoryUnavailable(Exception):
    """History is off, or the database does not answer."""


class History:
    def __init__(self, url: str):
        self.url = url

    def connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self.url, connect_timeout=3, row_factory=dict_row)
        except psycopg.OperationalError as error:
            raise HistoryUnavailable("the database does not answer") from error

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
                "SELECT request_id, category, priority, confidence, score,"
                " model_version, created_at"
                " FROM classifications ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
