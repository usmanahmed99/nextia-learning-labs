"""Every SQL statement of the API, in one place.

The rules (Module 3 of the databases course):
- Values always go to the database as parameters (%s or %(name)s), never inside
  the SQL text. The SQL text is built only from fixed pieces in this file.
- A function gets a connection; the caller decides where the transaction starts
  and ends.
The rule of the authentication course (Module 4):
- Every function that reads or writes an organization's records takes `tenant_id` as a
  required keyword argument, and every statement has `tenant_id = %(tenant_id)s` in it.
  The value comes from the caller's checked membership (ticket_api/tenancy.py), never
  from the request body or a header. A record of another organization is "not found".
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
    tenant_id: str,
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
    where, params = ["t.tenant_id = %(tenant_id)s"], {"limit": limit + 1, "tenant_id": tenant_id}
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
        + " WHERE " + " AND ".join(where)
        + " ORDER BY t.created_at DESC, t.ticket_id DESC LIMIT %(limit)s"
    )
    return sql, params


def list_tickets(conn: psycopg.Connection, *, tenant_id: str, limit: int = 20, **filters) -> dict:
    """One page of one organization's tickets, newest first, and the next cursor (one query)."""
    sql, params = list_query(tenant_id=tenant_id, limit=limit, **filters)
    rows = conn.execute(sql, params).fetchall()
    more = len(rows) > limit
    rows = rows[:limit]
    last = rows[-1] if rows else None
    return {
        "items": rows,
        "next": encode_cursor(last["created_at"], last["ticket_id"]) if more else None,
    }


def get_ticket(conn: psycopg.Connection, ticket_id: str, *, tenant_id: str) -> dict:
    p = {"id": ticket_id, "tenant_id": tenant_id}
    ticket = conn.execute(
        "SELECT t.*, c.name AS customer_name FROM tickets t"
        " JOIN customers c ON c.tenant_id = t.tenant_id AND c.customer_id = t.customer_id"
        " WHERE t.tenant_id = %(tenant_id)s AND t.ticket_id = %(id)s",
        p,
    ).fetchone()
    if ticket is None:  # also when the ticket exists in another organization
        raise NotFound(f"Ticket {ticket_id} does not exist.")
    ticket["messages"] = conn.execute(
        "SELECT message_id, author, body, created_at FROM messages"
        " WHERE tenant_id = %(tenant_id)s AND ticket_id = %(id)s ORDER BY created_at, message_id",
        p,
    ).fetchall()
    ticket["attachments"] = conn.execute(
        "SELECT attachment_id, file_name, content_type, size_bytes, status, uploaded_at FROM"
        " attachments WHERE tenant_id = %(tenant_id)s AND ticket_id = %(id)s"
        " AND status = 'stored' ORDER BY uploaded_at, attachment_id",
        p,
    ).fetchall()
    return ticket


def add_message(
    conn: psycopg.Connection, ticket_id: str, author: str, body: str, *, tenant_id: str
) -> dict:
    """Add a message and update the ticket's counts in one transaction.

    The ticket row is locked first (FOR UPDATE): two messages that arrive at the
    same time wait for each other, so neither count update is lost."""
    with conn.transaction():
        ticket = conn.execute(
            "SELECT status FROM tickets WHERE tenant_id = %s AND ticket_id = %s FOR UPDATE",
            (tenant_id, ticket_id),
        ).fetchone()
        if ticket is None:
            raise NotFound(f"Ticket {ticket_id} does not exist.")
        message = conn.execute(
            "INSERT INTO messages (tenant_id, ticket_id, author, body) VALUES (%s, %s, %s, %s)"
            " RETURNING message_id, ticket_id, author, body, created_at",
            (tenant_id, ticket_id, author, body),
        ).fetchone()
        # A customer's message opens the ticket again; an agent's reply waits for the customer.
        status = "open" if author == "customer" else "pending"
        conn.execute(
            "UPDATE tickets SET message_count = message_count + 1, last_message_at = %s,"
            " status = %s, closed_at = NULL, updated_at = now()"
            " WHERE tenant_id = %s AND ticket_id = %s",
            (message["created_at"], status, tenant_id, ticket_id),
        )
    return message


def ticket_exists(conn: psycopg.Connection, ticket_id: str, *, tenant_id: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM tickets WHERE tenant_id = %s AND ticket_id = %s", (tenant_id, ticket_id)
        ).fetchone()
        is not None
    )


# ---------- people (the authentication course) ----------


def get_user(conn: psycopg.Connection, user_id: str) -> dict | None:
    return conn.execute(
        "SELECT user_id, name, email, platform_role FROM users WHERE user_id = %s", (user_id,)
    ).fetchone()


def upsert_user(
    conn: psycopg.Connection, user_id: str, name: str | None, email: str | None
) -> None:
    """A person who signs in for the first time gets a row (name and email from the ID token)."""
    conn.execute(
        "INSERT INTO users (user_id, name, email) VALUES (%s, %s, %s)"
        " ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, email = EXCLUDED.email",
        (user_id, name or user_id, email or f"{user_id}@unknown.example"),
    )


def membership_role(conn: psycopg.Connection, tenant_id: str, user_id: str) -> str | None:
    """The role of a user in an active organization, or None (not a member, or no such
    organization: the caller cannot tell the two apart, on purpose)."""
    row = conn.execute(
        "SELECT m.role FROM memberships m JOIN tenants t USING (tenant_id)"
        " WHERE m.tenant_id = %s AND m.user_id = %s AND t.status = 'active'",
        (tenant_id, user_id),
    ).fetchone()
    return row["role"] if row else None


def active_support_grant(conn: psycopg.Connection, tenant_id: str, user_id: str) -> dict | None:
    """A platform administrator's support grant for this organization that is still valid."""
    return conn.execute(
        "SELECT g.grant_id, g.reason, g.expires_at FROM support_grants g"
        " JOIN users u USING (user_id) JOIN tenants t USING (tenant_id)"
        " WHERE g.tenant_id = %s AND g.user_id = %s AND u.platform_role = 'platform_admin'"
        " AND t.status = 'active' AND g.revoked_at IS NULL AND g.expires_at > now()"
        " ORDER BY g.expires_at DESC LIMIT 1",
        (tenant_id, user_id),
    ).fetchone()


def memberships_of(conn: psycopg.Connection, user_id: str) -> list[dict]:
    """The organizations a user is a member of, with the role in each."""
    return conn.execute(
        "SELECT m.tenant_id, t.name AS tenant_name, m.role FROM memberships m"
        " JOIN tenants t USING (tenant_id) WHERE m.user_id = %s AND t.status = 'active'"
        " ORDER BY m.tenant_id",
        (user_id,),
    ).fetchall()


# ---------- members and invitations (the authentication course, Module 5) ----------


class Conflict(Exception):
    """The change would break a rule (the last owner, an invitation already used)."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def list_members(conn: psycopg.Connection, *, tenant_id: str) -> list[dict]:
    return conn.execute(
        "SELECT m.user_id, u.name, m.role, m.created_at AS since FROM memberships m"
        " JOIN users u USING (user_id) WHERE m.tenant_id = %s ORDER BY m.role, m.user_id",
        (tenant_id,),
    ).fetchall()


def _owners(conn: psycopg.Connection, tenant_id: str) -> int:
    return conn.execute(
        "SELECT count(*) AS n FROM memberships WHERE tenant_id = %s AND role = 'owner'",
        (tenant_id,),
    ).fetchone()["n"]


def change_role(conn: psycopg.Connection, user_id: str, role: str, *, tenant_id: str) -> dict:
    with conn.transaction():
        row = conn.execute(
            "SELECT role FROM memberships WHERE tenant_id = %s AND user_id = %s FOR UPDATE",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            raise NotFound(f"{user_id} is not a member.")
        if row["role"] == "owner" and role != "owner" and _owners(conn, tenant_id) == 1:
            raise Conflict("The organization needs at least one owner.", "last_owner")
        conn.execute(
            "UPDATE memberships SET role = %s WHERE tenant_id = %s AND user_id = %s",
            (role, tenant_id, user_id),
        )
    return {"before": row["role"], "after": role}


def remove_member(conn: psycopg.Connection, user_id: str, *, tenant_id: str) -> str:
    with conn.transaction():
        row = conn.execute(
            "SELECT role FROM memberships WHERE tenant_id = %s AND user_id = %s FOR UPDATE",
            (tenant_id, user_id),
        ).fetchone()
        if row is None:
            raise NotFound(f"{user_id} is not a member.")
        if row["role"] == "owner" and _owners(conn, tenant_id) == 1:
            raise Conflict("The organization needs at least one owner.", "last_owner")
        conn.execute(
            "DELETE FROM memberships WHERE tenant_id = %s AND user_id = %s", (tenant_id, user_id)
        )
    return row["role"]


def create_invitation(
    conn: psycopg.Connection,
    invitation_id: str,
    email: str,
    role: str,
    code_sha256: str,
    invited_by: str,
    hours: int,
    *,
    tenant_id: str,
) -> dict:
    return conn.execute(
        "INSERT INTO invitations (invitation_id, tenant_id, email, role, code_sha256, invited_by,"
        " expires_at) VALUES (%s, %s, lower(%s), %s, %s, %s, now() + make_interval(hours => %s))"
        " RETURNING invitation_id, email, role, expires_at",
        (invitation_id, tenant_id, email, role, code_sha256, invited_by, hours),
    ).fetchone()


def accept_invitation(conn: psycopg.Connection, code_sha256: str, user: dict) -> dict:
    """Make the membership of an invitation, once, for the person whose email it names."""
    with conn.transaction():
        inv = conn.execute(
            "SELECT i.*, t.status AS tenant_status FROM invitations i JOIN tenants t"
            " USING (tenant_id) WHERE code_sha256 = %s FOR UPDATE OF i",
            (code_sha256,),
        ).fetchone()
        if inv is None or inv["tenant_status"] != "active" or inv["revoked_at"]:
            raise NotFound("This invitation does not exist.")
        if inv["accepted_at"] is not None:
            raise Conflict("This invitation was used already.", "invitation_used")
        if inv["expires_at"] <= conn.execute("SELECT now() AS n").fetchone()["n"]:
            raise Conflict("This invitation has expired. Ask for a new one.", "invitation_expired")
        if inv["email"] != user["email"].lower():
            raise NotFound("This invitation does not exist.")  # it is for someone else
        conn.execute(
            "INSERT INTO memberships (tenant_id, user_id, role) VALUES (%s, %s, %s)"
            " ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = EXCLUDED.role",
            (inv["tenant_id"], user["user_id"], inv["role"]),
        )
        conn.execute(
            "UPDATE invitations SET accepted_at = now(), accepted_by = %s"
            " WHERE invitation_id = %s",
            (user["user_id"], inv["invitation_id"]),
        )
    return {"tenant_id": inv["tenant_id"], "role": inv["role"]}


# ---------- jobs (the authentication course, Module 5) ----------


def create_job(
    conn: psycopg.Connection, job_id: str, actor_id: str, kind: str, params: dict, *, tenant_id: str
) -> dict:
    from psycopg.types.json import Jsonb

    return conn.execute(
        "INSERT INTO jobs (job_id, tenant_id, actor_id, kind, params) VALUES (%s, %s, %s, %s, %s)"
        " RETURNING *",
        (job_id, tenant_id, actor_id, kind, Jsonb(params)),
    ).fetchone()


def get_job(conn: psycopg.Connection, job_id: str, *, tenant_id: str) -> dict:
    row = conn.execute(
        "SELECT * FROM jobs WHERE tenant_id = %s AND job_id = %s", (tenant_id, job_id)
    ).fetchone()
    if row is None:
        raise NotFound(f"Job {job_id} does not exist.")
    return row


def export_rows(
    conn: psycopg.Connection, *, tenant_id: str, status: str | None, team: str | None
) -> list[dict]:
    return conn.execute(
        "SELECT ticket_id, customer_id, subject, team, priority, status, created_at FROM tickets"
        " WHERE tenant_id = %(t)s AND (%(s)s::text IS NULL OR status = %(s)s)"
        " AND (%(m)s::text IS NULL OR team = %(m)s) ORDER BY created_at, ticket_id",
        {"t": tenant_id, "s": status, "m": team},
    ).fetchall()


# ---------- help documents (the authentication course, Module 4) ----------


def search_documents(
    conn: psycopg.Connection, q: str, *, tenant_id: str, staff: bool, limit: int = 5
) -> list[dict]:
    """The current documents of one organization that match the words of q, best first.
    Staff-only documents only when `staff` is true (the caller's role allows them)."""
    return conn.execute(
        "SELECT doc_id, version, title, access,"
        " ts_headline('english', body, query, 'MaxFragments=1, MaxWords=18, MinWords=8')"
        " AS snippet, ts_rank(to_tsvector('english', title || ' ' || body), query) AS rank"
        " FROM documents, plainto_tsquery('english', %(q)s) AS query"
        " WHERE tenant_id = %(tenant_id)s AND effective_to IS NULL"
        " AND (access = 'public' OR %(staff)s)"
        " AND to_tsvector('english', title || ' ' || body) @@ query"
        " ORDER BY rank DESC, doc_id LIMIT %(limit)s",
        {"q": q, "tenant_id": tenant_id, "staff": staff, "limit": limit},
    ).fetchall()


# ---------- attachments (Module 5) ----------


def create_attachment(
    conn: psycopg.Connection,
    tenant_id: str,
    attachment_id: str,
    ticket_id: str,
    file_name: str,
    content_type: str,
    size_bytes: int,
    object_key: str,
) -> dict:
    return conn.execute(
        "INSERT INTO attachments (tenant_id, attachment_id, ticket_id, file_name, content_type,"
        " size_bytes, object_key, status)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')"
        " RETURNING attachment_id, ticket_id, file_name, content_type, size_bytes, object_key,"
        " status, created_at",
        (tenant_id, attachment_id, ticket_id, file_name, content_type, size_bytes, object_key),
    ).fetchone()


def get_attachment(
    conn: psycopg.Connection, attachment_id: str, *, tenant_id: str, lock: bool = False
) -> dict:
    row = conn.execute(
        "SELECT * FROM attachments WHERE tenant_id = %s AND attachment_id = %s"
        + (" FOR UPDATE" if lock else ""),
        (tenant_id, attachment_id),
    ).fetchone()
    if row is None:
        raise NotFound(f"Attachment {attachment_id} does not exist.")
    return row


def finish_attachment(
    conn: psycopg.Connection,
    attachment_id: str,
    *,
    tenant_id: str,
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
        " WHERE tenant_id = %(tenant_id)s AND attachment_id = %(id)s AND status = 'pending'"
        " RETURNING *",
        {
            "status": "stored" if stored else "rejected",
            "stored": stored,
            "size": size_bytes,
            "sha": sha256,
            "id": attachment_id,
            "tenant_id": tenant_id,
        },
    ).fetchone()
    return row or get_attachment(conn, attachment_id, tenant_id=tenant_id)


# ---------- vectors (Module 5) ----------


def current_embedding_version(conn: psycopg.Connection) -> str | None:
    row = conn.execute("SELECT version FROM embedding_versions WHERE is_current").fetchone()
    return row["version"] if row else None


def similar_tickets(
    conn: psycopg.Connection,
    ticket_id: str,
    *,
    tenant_id: str,
    k: int = 5,
    version: str,
    team: str | None = None,
    status: str | None = None,
    exact: bool = False,
) -> list[dict]:
    """The k tickets whose vectors are closest to this ticket's vector (cosine distance),
    with the same embedding version, IN THE SAME ORGANIZATION. Filters (organization, team,
    status) are applied in the same query: the HNSW index finds candidates of every
    organization, and the iterative scan reads on until k rows pass the filters.

    The version goes into the SQL text as a quoted literal (psycopg.sql.Literal), not as a
    parameter: the approximate index is a partial index for one version, and PostgreSQL can
    use it only when it sees the version's value while it plans the query. The version comes
    from the embedding_versions table, never from the request.

    exact=False lets PostgreSQL use the HNSW index. Its iterative scan keeps reading the
    index until k rows pass the filters (pgvector 0.8)."""
    source = conn.execute(
        "SELECT embedding::text AS embedding FROM ticket_embeddings"
        " WHERE tenant_id = %s AND ticket_id = %s AND embedding_version = %s",
        (tenant_id, ticket_id, version),
    ).fetchone()
    if source is None:
        raise NotFound(f"Ticket {ticket_id} has no vector of version {version}.")
    where = [
        sql.SQL("e.embedding_version = {}").format(sql.Literal(version)),
        sql.SQL("e.ticket_id <> %(ticket_id)s"),
        sql.SQL("e.tenant_id = %(tenant_id)s"),
    ]
    params = {"ticket_id": ticket_id, "vector": source["embedding"], "k": k, "tenant_id": tenant_id}
    for column, value in (("team", team), ("status", status)):
        if value is not None:
            where.append(
                sql.SQL("t.{} = {}").format(sql.Identifier(column), sql.Placeholder(column))
            )
            params[column] = value
    query = sql.SQL(
        "SELECT t.ticket_id, t.subject, t.team, t.status, t.created_at,"
        " e.embedding <=> %(vector)s::vector AS distance"
        " FROM ticket_embeddings e"
        " JOIN tickets t ON t.tenant_id = e.tenant_id AND t.ticket_id = e.ticket_id"
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
