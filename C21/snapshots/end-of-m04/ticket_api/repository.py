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
from psycopg import sql

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
        "SELECT attachment_id, file_name, content_type, size_bytes, status, uploaded_at FROM"
        " attachments"
        " WHERE ticket_id = %s AND status = 'stored' ORDER BY uploaded_at, attachment_id",
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


# ---------- attachments (Module 5) ----------


def create_attachment(
    conn: psycopg.Connection,
    attachment_id: str,
    ticket_id: str,
    file_name: str,
    content_type: str,
    size_bytes: int,
    object_key: str,
) -> dict:
    return conn.execute(
        "INSERT INTO attachments (attachment_id, ticket_id, file_name, content_type,"
        " size_bytes, object_key, status)"
        " VALUES (%s, %s, %s, %s, %s, %s, 'pending')"
        " RETURNING attachment_id, ticket_id, file_name, content_type, size_bytes, object_key,"
        " status, created_at",
        (attachment_id, ticket_id, file_name, content_type, size_bytes, object_key),
    ).fetchone()


def get_attachment(conn: psycopg.Connection, attachment_id: str, *, lock: bool = False) -> dict:
    row = conn.execute(
        "SELECT * FROM attachments WHERE attachment_id = %s" + (" FOR UPDATE" if lock else ""),
        (attachment_id,),
    ).fetchone()
    if row is None:
        raise NotFound(f"Attachment {attachment_id} does not exist.")
    return row


def finish_attachment(
    conn: psycopg.Connection,
    attachment_id: str,
    *,
    stored: bool,
    size_bytes: int,
    sha256: str | None,
) -> dict:
    """Mark a pending upload as stored (with its real size and checksum) or rejected.
    Only a pending row changes; if another request finished it first, return that result."""
    row = conn.execute(
        "UPDATE attachments SET status = %(status)s,"
        " size_bytes = CASE WHEN %(stored)s THEN %(size)s ELSE size_bytes END,"
        " sha256 = %(sha)s, uploaded_at = CASE WHEN %(stored)s THEN now() END"
        " WHERE attachment_id = %(id)s AND status = 'pending' RETURNING *",
        {
            "status": "stored" if stored else "rejected",
            "stored": stored,
            "size": size_bytes,
            "sha": sha256,
            "id": attachment_id,
        },
    ).fetchone()
    return row or get_attachment(conn, attachment_id)


# ---------- vectors (Module 5) ----------


def current_embedding_version(conn: psycopg.Connection) -> str | None:
    row = conn.execute("SELECT version FROM embedding_versions WHERE is_current").fetchone()
    return row["version"] if row else None


def similar_tickets(
    conn: psycopg.Connection,
    ticket_id: str,
    *,
    k: int = 5,
    version: str,
    team: str | None = None,
    status: str | None = None,
    exact: bool = False,
) -> list[dict]:
    """The k tickets whose vectors are closest to this ticket's vector (cosine distance),
    with the same embedding version. Filters (team, status) are applied in the same query.

    The version goes into the SQL text as a quoted literal (psycopg.sql.Literal), not as a
    parameter: the approximate index is a partial index for one version, and PostgreSQL can
    use it only when it sees the version's value while it plans the query. The version comes
    from the embedding_versions table, never from the request.

    exact=False lets PostgreSQL use the HNSW index. Its iterative scan keeps reading the
    index until k rows pass the filters (pgvector 0.8)."""
    source = conn.execute(
        "SELECT embedding::text AS embedding FROM ticket_embeddings"
        " WHERE ticket_id = %s AND embedding_version = %s",
        (ticket_id, version),
    ).fetchone()
    if source is None:
        raise NotFound(f"Ticket {ticket_id} has no vector of version {version}.")
    where = [
        sql.SQL("e.embedding_version = {}").format(sql.Literal(version)),
        sql.SQL("e.ticket_id <> %(ticket_id)s"),
    ]
    params = {"ticket_id": ticket_id, "vector": source["embedding"], "k": k}
    for column, value in (("team", team), ("status", status)):
        if value is not None:
            where.append(
                sql.SQL("t.{} = {}").format(sql.Identifier(column), sql.Placeholder(column))
            )
            params[column] = value
    query = sql.SQL(
        "SELECT t.ticket_id, t.subject, t.team, t.status, t.created_at,"
        " e.embedding <=> %(vector)s::vector AS distance"
        " FROM ticket_embeddings e JOIN tickets t ON t.ticket_id = e.ticket_id"
        " WHERE {where} ORDER BY e.embedding <=> %(vector)s::vector LIMIT %(k)s"
    ).format(where=sql.SQL(" AND ").join(where))
    with conn.transaction():
        if exact:
            conn.execute("SET LOCAL enable_indexscan = off")
        else:
            conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
        rows = conn.execute(query, params).fetchall()
    rows.sort(key=lambda r: (r["distance"], r["ticket_id"]))  # relaxed order: sort the k rows again
    return rows


# ---------- new tickets and their AI work (the scaling course) ----------


def customer_exists(conn: psycopg.Connection, customer_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM customers WHERE customer_id = %s", (customer_id,))
    return row.fetchone() is not None


def insert_ticket(
    conn: psycopg.Connection, customer_id: str, subject: str, body: str, channel: str
) -> dict:
    """A new open ticket. It goes to the team "other" with priority 2 until it is classified."""
    try:
        return conn.execute(
            "INSERT INTO tickets (ticket_id, customer_id, subject, body, channel, team, priority)"
            " VALUES ('T-' || nextval('ticket_number_seq'), %s, %s, %s, %s, 'other', 2)"
            " RETURNING ticket_id, customer_id, subject, body, team, priority, status, created_at",
            (customer_id, subject, body, channel),
        ).fetchone()
    except psycopg.errors.ForeignKeyViolation:
        raise NotFound(f"Customer {customer_id} does not exist.") from None


def save_ai_run(conn: psycopg.Connection, ticket_id: str, run: dict) -> int:
    """One row in ai_runs: the task, model, prompt, tokens, cost, time and output."""
    return conn.execute(
        "INSERT INTO ai_runs (ticket_id, task, model, prompt_version, tokens_in, tokens_out,"
        " cost_usd, latency_ms, status, output, created_at)"
        " VALUES (%(ticket_id)s, %(task)s, %(model)s, %(prompt_version)s, %(tokens_in)s,"
        " %(tokens_out)s, %(cost_usd)s, %(latency_ms)s, %(status)s, %(output)s, now())"
        " RETURNING run_id",
        {"ticket_id": ticket_id, **run},
    ).fetchone()["run_id"]


def set_classification(conn: psycopg.Connection, ticket_id: str, team: str, priority: int) -> None:
    conn.execute(
        "UPDATE tickets SET team = %s, priority = %s, updated_at = now() WHERE ticket_id = %s",
        (team, priority, ticket_id),
    )


def save_embedding(
    conn: psycopg.Connection, ticket_id: str, version: str, vector: list[float], source_sha256: str
) -> None:
    conn.execute(
        "INSERT INTO ticket_embeddings (ticket_id, embedding_version, embedding, source_sha256)"
        " VALUES (%s, %s, %s::vector, %s)"
        " ON CONFLICT (ticket_id, embedding_version) DO UPDATE"
        " SET embedding = EXCLUDED.embedding, source_sha256 = EXCLUDED.source_sha256",
        (ticket_id, version, "[" + ",".join(f"{x:.7g}" for x in vector) + "]", source_sha256),
    )


# ---------- answers to questions (the scaling course, Module 3) ----------


def search_documents(
    conn: psycopg.Connection, question: str, access: list[str], limit: int = 2
) -> list[dict]:
    """The current documents that match the question best, among those the caller may read."""
    return conn.execute(
        "SELECT doc_id, version, title, body FROM documents"
        " WHERE access = ANY(%(access)s) AND effective_to IS NULL"
        " AND to_tsvector('english', title || ' ' || body)"
        " @@ websearch_to_tsquery('english', %(q)s)"
        " ORDER BY ts_rank(to_tsvector('english', title || ' ' || body),"
        " websearch_to_tsquery('english', %(q)s)) DESC, doc_id LIMIT %(limit)s",
        {"access": access, "q": question.replace(" ", " or "), "limit": limit},
    ).fetchall()


def documents_version(conn: psycopg.Connection) -> str:
    """A short fingerprint of all documents: it changes when any document changes."""
    row = conn.execute(
        "SELECT left(md5(string_agg(doc_id || ':' || version || ':' || sha256, ','"
        " ORDER BY doc_id, version)), 12) AS v FROM documents"
    ).fetchone()
    return row["v"] or "none"


def latest_tickets(conn: psycopg.Connection, customer_id: str, limit: int = 3) -> list[dict]:
    return conn.execute(
        "SELECT ticket_id, subject, status FROM tickets WHERE customer_id = %s"
        " ORDER BY created_at DESC, ticket_id DESC LIMIT %s",
        (customer_id, limit),
    ).fetchall()


def ticket_customer(conn: psycopg.Connection, ticket_id: str) -> str | None:
    row = conn.execute("SELECT customer_id FROM tickets WHERE ticket_id = %s", (ticket_id,))
    found = row.fetchone()
    return found["customer_id"] if found else None


# ---------- the AI work of a job (the scaling course, Module 4) ----------


def ticket_for_work(conn: psycopg.Connection, ticket_id: str) -> dict | None:
    return conn.execute(
        "SELECT ticket_id, customer_id, subject, body FROM tickets WHERE ticket_id = %s",
        (ticket_id,),
    ).fetchone()


def job_runs(conn: psycopg.Connection, job_id: int) -> dict[str, dict]:
    """The AI results that a job has made already, by task."""
    rows = conn.execute(
        "SELECT task, model, output, tokens_in, tokens_out, cost_usd, latency_ms"
        " FROM ai_runs WHERE job_id = %s",
        (job_id,),
    ).fetchall()
    return {r["task"]: r for r in rows}


def save_job_ai_run(conn: psycopg.Connection, ticket_id: str, job_id: int, run: dict) -> bool:
    """Save one task's result of a job, once. False if this job already has it (a second
    delivery of the same job): the database refuses a second row (job_id, task)."""
    return (
        conn.execute(
            "INSERT INTO ai_runs (ticket_id, job_id, task, model, prompt_version, tokens_in,"
            " tokens_out, cost_usd, latency_ms, status, output, created_at)"
            " VALUES (%(ticket_id)s, %(job_id)s, %(task)s, %(model)s, %(prompt_version)s,"
            " %(tokens_in)s, %(tokens_out)s, %(cost_usd)s, %(latency_ms)s, %(status)s,"
            " %(output)s, now())"
            " ON CONFLICT (job_id, task) WHERE job_id IS NOT NULL DO NOTHING",
            {"ticket_id": ticket_id, "job_id": job_id, **run},
        ).rowcount
        == 1
    )
