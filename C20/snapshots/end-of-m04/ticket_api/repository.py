"""Every SQL statement of the API, in one place.

The rules (Module 3 of the databases course):
- Values always go to the database as parameters (%s or %(name)s), never inside
  the SQL text. The SQL text is built only from fixed pieces in this file.
- A function gets a connection; the caller decides where the transaction starts
  and ends.
"""

import base64
from datetime import datetime

import psycopg

LIST_COLUMNS = """
    t.ticket_id, t.customer_id, c.name AS customer_name, t.subject, t.team, t.priority,
    t.status, t.created_at, t.message_count, t.last_message_at,
    r.model AS last_run_model, r.status AS last_run_status
"""


class NotFound(Exception):
    """The record does not exist."""


class InvalidCursor(ValueError):
    """The `after` value of a list request is not one that the API made."""


def encode_cursor(created_at: datetime, ticket_id: str) -> str:
    raw = f"{created_at.isoformat()}|{ticket_id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        created, ticket_id = raw.split("|")
        return datetime.fromisoformat(created), ticket_id
    except (ValueError, UnicodeDecodeError):
        raise InvalidCursor(cursor) from None


def list_query(
    *,
    status: str | None = None,
    team: str | None = None,
    customer_id: str | None = None,
    limit: int = 20,
    after: str | None = None,
) -> tuple[str, dict]:
    """The SQL of one page of the ticket list, and its parameters.

    Keyset pagination: the page after `after` starts below the last row of the previous
    page, so the database reads only `limit` rows from the index, however deep the page
    is. The customer's name and the latest AI run come in the same query (no N+1)."""
    where, params = [], {"limit": limit + 1}
    for column, value in (("status", status), ("team", team), ("customer_id", customer_id)):
        if value is not None:
            where.append(f"t.{column} = %({column})s")
            params[column] = value
    if after:
        params["after_at"], params["after_id"] = decode_cursor(after)
        where.append("(t.created_at, t.ticket_id) < (%(after_at)s, %(after_id)s)")
    sql = (
        f"SELECT {LIST_COLUMNS}"
        " FROM tickets t JOIN customers c ON c.customer_id = t.customer_id"
        " LEFT JOIN LATERAL (SELECT a.model, a.status FROM ai_runs a WHERE a.ticket_id ="
        " t.ticket_id"
        " ORDER BY a.created_at DESC LIMIT 1) r ON true"
        + (" WHERE " + " AND ".join(where) if where else "")
        + " ORDER BY t.created_at DESC, t.ticket_id DESC LIMIT %(limit)s"
    )
    return sql, params


def list_tickets(conn: psycopg.Connection, *, limit: int = 20, **filters) -> dict:
    """One page of tickets, newest first, and the cursor of the next page (one query)."""
    sql, params = list_query(limit=limit, **filters)
    rows = conn.execute(sql, params).fetchall()
    more = len(rows) > limit
    rows = rows[:limit]
    last = rows[-1] if rows else None
    return {
        "items": rows,
        "next": encode_cursor(last["created_at"], last["ticket_id"]) if more else None,
    }


def get_ticket(conn: psycopg.Connection, ticket_id: str) -> dict:
    ticket = conn.execute(
        "SELECT t.*, c.name AS customer_name FROM tickets t"
        " JOIN customers c ON c.customer_id = t.customer_id WHERE t.ticket_id = %s",
        (ticket_id,),
    ).fetchone()
    if ticket is None:
        raise NotFound(f"Ticket {ticket_id} does not exist.")
    ticket["messages"] = conn.execute(
        "SELECT message_id, author, body, created_at FROM messages"
        " WHERE ticket_id = %s ORDER BY created_at, message_id",
        (ticket_id,),
    ).fetchall()
    ticket["attachments"] = conn.execute(
        "SELECT attachment_id, file_name, content_type, size_bytes, uploaded_at FROM"
        " attachments"
        " WHERE ticket_id = %s ORDER BY uploaded_at, attachment_id",
        (ticket_id,),
    ).fetchall()
    return ticket


def add_message(conn: psycopg.Connection, ticket_id: str, author: str, body: str) -> dict:
    """Add a message and update the ticket's counts in one transaction.

    The ticket row is locked first (FOR UPDATE): two messages that arrive at the
    same time wait for each other, so neither count update is lost."""
    with conn.transaction():
        ticket = conn.execute(
            "SELECT status FROM tickets WHERE ticket_id = %s FOR UPDATE", (ticket_id,)
        ).fetchone()
        if ticket is None:
            raise NotFound(f"Ticket {ticket_id} does not exist.")
        message = conn.execute(
            "INSERT INTO messages (ticket_id, author, body) VALUES (%s, %s, %s)"
            " RETURNING message_id, ticket_id, author, body, created_at",
            (ticket_id, author, body),
        ).fetchone()
        # A customer's message opens the ticket again; an agent's reply waits for the customer.
        status = "open" if author == "customer" else "pending"
        conn.execute(
            "UPDATE tickets SET message_count = message_count + 1, last_message_at = %s,"
            " status = %s, closed_at = NULL, updated_at = now() WHERE ticket_id = %s",
            (message["created_at"], status, ticket_id),
        )
    return message


def ticket_exists(conn: psycopg.Connection, ticket_id: str) -> bool:
    return (
        conn.execute("SELECT 1 FROM tickets WHERE ticket_id = %s", (ticket_id,)).fetchone()
        is not None
    )
