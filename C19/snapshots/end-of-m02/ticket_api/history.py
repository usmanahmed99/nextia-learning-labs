"""Keep a record of the classifications in PostgreSQL.

The record has the result of each classification, never the ticket's text.
History is optional: without DATABASE_URL the API classifies tickets and
keeps no record.
"""

import psycopg
from psycopg.rows import dict_row

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS classifications (
    id            bigserial PRIMARY KEY,
    request_id    text        NOT NULL,
    category      text        NOT NULL,
    priority      smallint    NOT NULL,
    confidence    real        NOT NULL,
    model_version text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
)
"""


class HistoryUnavailable(Exception):
    """History is off, or the database does not answer."""


class History:
    def __init__(self, url: str):
        self.url = url
        self.table_ready = False

    def connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self.url, connect_timeout=3, row_factory=dict_row)
        except psycopg.OperationalError as error:
            raise HistoryUnavailable("the database does not answer") from error

    def setup(self) -> None:
        """Make the table if it does not exist."""
        with self.connect() as conn:
            conn.execute(CREATE_TABLE)
        self.table_ready = True

    def check(self) -> None:
        with self.connect() as conn:
            conn.execute("SELECT 1")

    def add(self, request_id: str, result: dict) -> None:
        if not self.table_ready:
            self.setup()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO classifications"
                " (request_id, category, priority, confidence, model_version)"
                " VALUES (%s, %s, %s, %s, %s)",
                (
                    request_id,
                    result["category"],
                    result["priority"],
                    result["confidence"],
                    result["model_version"],
                ),
            )

    def recent(self, limit: int) -> list[dict]:
        if not self.table_ready:
            self.setup()
        with self.connect() as conn:
            return conn.execute(
                "SELECT request_id, category, priority, confidence, model_version,"
                " created_at FROM classifications ORDER BY id DESC LIMIT %s",
                (limit,),
            ).fetchall()
