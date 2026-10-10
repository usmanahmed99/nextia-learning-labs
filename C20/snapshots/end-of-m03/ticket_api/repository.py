"""Every SQL statement of the API, in one place.

The rules (Module 3 of the databases course):
- Values always go to the database as parameters (%s or %(name)s), never inside
  the SQL text. The SQL text is built only from fixed pieces in this file.
- A function gets a connection; the caller decides where the transaction starts
  and ends.
"""

import psycopg


class NotFound(Exception):
    """The record does not exist."""


def list_query(
    *,
    status: str | None = None,
    team: str | None = None,
    customer_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[str, dict]:
    """The SQL of one page of the ticket list, and its parameters: the newest first,
    `limit` rows after skipping `offset` rows."""
    where, params = [], {"limit": limit, "offset": offset}
    for column, value in (("status", status), ("team", team), ("customer_id", customer_id)):
        if value is not None:
            where.append(f"t.{column} = %({column})s")
            params[column] = value
    sql = (
        "SELECT * FROM tickets t"
        + (" WHERE " + " AND ".join(where) if where else "")
        + " ORDER BY t.created_at DESC, t.ticket_id DESC LIMIT %(limit)s OFFSET %(offset)s"
    )
    return sql, params


def list_tickets(conn: psycopg.Connection, *, limit: int = 20, offset: int = 0, **filters) -> dict:
    """One page of tickets, newest first, with the customer's name and the latest AI run."""
    sql, params = list_query(limit=limit, offset=offset, **filters)
    items = []
    for t in conn.execute(sql, params).fetchall():
        customer = conn.execute(
            "SELECT name FROM customers WHERE customer_id = %s", (t["customer_id"],)
        ).fetchone()
        run = conn.execute(
            "SELECT model, status FROM ai_runs WHERE ticket_id = %s"
            " ORDER BY created_at DESC LIMIT 1",
            (t["ticket_id"],),
        ).fetchone()
        items.append(
            {
                **t,
                "customer_name": customer["name"],
                "last_run_model": run["model"] if run else None,
                "last_run_status": run["status"] if run else None,
            }
        )
    return {"items": items, "next_offset": offset + limit if len(items) == limit else None}


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
