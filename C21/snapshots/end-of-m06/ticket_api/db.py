"""Connections to PostgreSQL: a pool that the app opens at start-up and closes at shutdown.

    with db.connection() as conn:       # borrow a connection; it goes back to the pool at the end
        with conn.transaction():        # one transaction: all of it happens, or none of it
            conn.execute(...)

Without the pool (DB_POOL=false) every `connection()` opens a new connection and
closes it at the end, as the project did before: kept so that both can be measured.

When the block ends with an error, the transaction is rolled back and the
connection still goes back to the pool: a failed request never keeps one.
"""

import contextvars
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

logger = logging.getLogger("ticket_api")

# How many queries the current request sent (for the X-DB-Queries header).
QUERIES: contextvars.ContextVar[list[int] | None] = contextvars.ContextVar("queries", default=None)


class DatabaseUnavailable(Exception):
    """The database does not answer."""


class DatabaseBusy(Exception):
    """Every connection of the pool is in use, and none came back in time."""


class CountingCursor(psycopg.Cursor):
    """A cursor that counts the queries of the current request."""

    def execute(self, query, params=None, **kwargs):
        counter = QUERIES.get()
        if counter is not None:
            counter[0] += 1
        return super().execute(query, params, **kwargs)


class Database:
    def __init__(
        self,
        url: str,
        *,
        pool: bool = True,
        min_size: int = 2,
        max_size: int = 10,
        timeout: float = 5.0,
        max_lifetime: float = 1800.0,
        max_idle: float = 300.0,
    ):
        self.url = url
        self.timeout = timeout
        self.connects = 0  # new connections opened without the pool
        self.pool = None
        if pool:
            self.pool = ConnectionPool(
                url,
                min_size=min_size,
                max_size=max_size,
                timeout=timeout,
                max_lifetime=max_lifetime,  # replace a connection after 30 minutes
                max_idle=max_idle,  # close extra idle connections after 5 minutes
                kwargs={
                    "row_factory": dict_row,
                    "cursor_factory": CountingCursor,
                    "connect_timeout": 3,
                },
                open=False,
                name="ticket-api",
            )

    def open(self) -> None:
        if self.pool is not None:
            self.pool.open(wait=False)

    def close(self) -> None:
        if self.pool is not None:
            self.pool.close()

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        if self.pool is None:
            try:
                conn = psycopg.connect(
                    self.url, connect_timeout=3, row_factory=dict_row, cursor_factory=CountingCursor
                )
            except psycopg.OperationalError as error:
                raise DatabaseUnavailable("the database does not answer") from error
            self.connects += 1
            with conn:  # commit at the end, roll back on an error, then close
                yield conn
            return
        try:
            with self.pool.connection() as conn:  # commit at the end, roll back on an error, return
                yield conn
        except PoolTimeout as error:
            stats = self.pool.get_stats()
            logger.warning(
                "pool timeout: size %s, waiting %s",
                stats.get("pool_size"),
                stats.get("requests_waiting"),
            )
            raise DatabaseBusy(f"no connection within {self.timeout} seconds") from error
        except psycopg.OperationalError as error:
            raise DatabaseUnavailable("the database does not answer") from error

    def stats(self) -> dict:
        if self.pool is None:
            return {"pool": False, "connections_opened": self.connects}
        s = self.pool.get_stats()
        return {
            "pool": True,
            "size": s.get("pool_size", 0),
            "available": s.get("pool_available", 0),
            "waiting": s.get("requests_waiting", 0),
            "max_size": self.pool.max_size,
        }
