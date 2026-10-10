"""Module 2: the database itself rejects duplicates, orphans and impossible values."""

import psycopg
import pytest


def insert_customer(conn, customer_id, email):
    conn.execute(
        "INSERT INTO customers (customer_id, name, email, segment, joined_on)"
        " VALUES (%s, 'Test Person', %s, 'home', '2026-10-01')",
        (customer_id, email),
    )


def test_a_duplicate_email_is_rejected_whatever_its_case(conn):
    insert_customer(conn, "C-9001", "new.person@example.com")
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_customer(conn, "C-9002", "New.Person@Example.com")


def test_a_duplicate_customer_id_is_rejected(conn):
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_customer(conn, "C-0001", "someone.else@example.com")


def test_an_orphan_message_is_rejected(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO messages (ticket_id, author, body) VALUES ('T-99999', 'agent', 'Hello')"
        )


def test_a_ticket_for_a_customer_who_does_not_exist_is_rejected(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO tickets (ticket_id, customer_id, subject, body, channel, team, priority)"
            " VALUES ('T-99999', 'C-9999', 'Hello', 'Hello', 'email', 'other', 2)"
        )


@pytest.mark.parametrize(
    "column, value",
    [
        ("priority", 4),
        ("status", "done"),
        ("team", "sales"),
        ("channel", "fax"),
        ("subject", "  "),
    ],
)
def test_impossible_values_are_rejected(conn, column, value):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(f"UPDATE tickets SET {column} = %s WHERE ticket_id = 'T-30001'", (value,))


def test_a_closed_ticket_needs_a_closing_time(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "UPDATE tickets SET status = 'closed', closed_at = NULL WHERE ticket_id = 'T-30002'"
        )


def test_the_old_orphan_messages_were_kept_apart(conn):
    rows = conn.execute("SELECT ticket_id FROM orphaned_messages ORDER BY ticket_id").fetchall()
    assert [r["ticket_id"] for r in rows] == ["T-29994", "T-29997", "T-29999"]


def test_deleting_a_ticket_deletes_its_messages_and_vector(conn):
    ticket = "T-30001"
    conn.execute("DELETE FROM ai_runs WHERE ticket_id = %s", (ticket,))
    conn.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket,))
    for table in ("messages", "ticket_embeddings"):
        n = conn.execute(
            f"SELECT count(*) AS n FROM {table} WHERE ticket_id = %s", (ticket,)
        ).fetchone()["n"]
        assert n == 0


def test_a_ticket_with_files_cannot_be_deleted(conn):
    """The database cannot delete a file in object storage, so it refuses."""
    ticket = conn.execute("SELECT ticket_id FROM attachments LIMIT 1").fetchone()["ticket_id"]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket,))


def test_ai_run_costs_stay_when_their_ticket_is_deleted(conn):
    run = conn.execute(
        "SELECT run_id, ticket_id FROM ai_runs WHERE ticket_id = 'T-30001' LIMIT 1"
    ).fetchone()
    conn.execute("DELETE FROM tickets WHERE ticket_id = 'T-30001'")
    row = conn.execute(
        "SELECT ticket_id, cost_usd FROM ai_runs WHERE run_id = %s", (run["run_id"],)
    ).fetchone()
    assert row["ticket_id"] is None and row["cost_usd"] is not None


def test_message_counts_match_the_messages(conn):
    wrong = conn.execute(
        "SELECT count(*) AS n FROM tickets t WHERE t.message_count <>"
        " (SELECT count(*) FROM messages m WHERE m.ticket_id = t.ticket_id)"
    ).fetchone()["n"]
    assert wrong == 0
