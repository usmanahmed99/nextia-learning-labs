"""Module 1 of the authentication course: two organizations in one database.

The database itself keeps each organization's records apart: a record of one shop cannot
point to a record of the other shop, and the rules that were global are per shop now."""

import psycopg
import pytest


def test_every_help_desk_row_has_an_organization(conn):
    for table in (
        "customers",
        "tickets",
        "messages",
        "attachments",
        "ai_runs",
        "documents",
        "ticket_embeddings",
    ):
        rows = conn.execute(f"SELECT DISTINCT tenant_id FROM {table} ORDER BY 1").fetchall()
        assert [r["tenant_id"] for r in rows] == ["bramble", "larkfield"], table


def test_a_message_cannot_point_to_another_organizations_ticket(conn):
    # T-40001 is Bramble Books' ticket; a Larkfield message for it is refused.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO messages (tenant_id, ticket_id, author, body)"
            " VALUES ('larkfield', 'T-40001', 'agent', 'Hello')"
        )


def test_a_ticket_cannot_belong_to_another_organizations_customer(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO tickets (tenant_id, ticket_id, customer_id, subject, body, channel,"
            " team, priority) VALUES ('bramble', 'T-49999', 'C-0001', 'Hi', 'Hi', 'email',"
            " 'other', 2)"
        )


def test_a_row_without_an_organization_is_refused(conn):
    with pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute(
            "INSERT INTO messages (ticket_id, author, body) VALUES ('T-30002', 'agent', 'Hi')"
        )


def test_two_shops_can_have_a_customer_with_the_same_email(conn):
    rows = conn.execute(
        "SELECT tenant_id, customer_id FROM customers WHERE lower(email) ="
        " 'olga.olsen@example.com' ORDER BY 1"
    ).fetchall()
    assert [(r["tenant_id"], r["customer_id"]) for r in rows] == [
        ("bramble", "B-20105"),
        ("larkfield", "C-0001"),
    ]
    with pytest.raises(psycopg.errors.UniqueViolation):  # but not twice in one shop
        conn.execute(
            "INSERT INTO customers (tenant_id, customer_id, name, email, segment, joined_on)"
            " VALUES ('bramble', 'B-20199', 'Olga', 'Olga.Olsen@example.com', 'home',"
            " '2026-10-01')"
        )


def test_two_shops_can_have_a_document_with_the_same_name(conn):
    rows = conn.execute(
        "SELECT tenant_id, title FROM documents WHERE doc_id = 'returns-policy' ORDER BY 1, version"
    ).fetchall()
    assert {r["tenant_id"] for r in rows} == {"bramble", "larkfield"}


def test_a_membership_has_a_known_role(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO memberships (tenant_id, user_id, role) VALUES ('bramble', 'usr-sam',"
            " 'admin')"
        )


def test_one_person_can_be_a_member_of_two_organizations(conn):
    rows = conn.execute(
        "SELECT tenant_id, role FROM memberships WHERE user_id = 'usr-camille' ORDER BY 1"
    ).fetchall()
    assert [(r["tenant_id"], r["role"]) for r in rows] == [
        ("bramble", "read_only"),
        ("larkfield", "staff"),
    ]


def test_a_person_without_membership_and_the_platform_administrator(conn):
    for user in ("usr-tomas", "usr-kwame"):
        n = conn.execute(
            "SELECT count(*) AS n FROM memberships WHERE user_id = %s", (user,)
        ).fetchone()["n"]
        assert n == 0
    role = conn.execute("SELECT platform_role FROM users WHERE user_id = 'usr-kwame'").fetchone()
    assert role["platform_role"] == "platform_admin"


def test_an_invitation_expires_after_it_was_made(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO invitations (invitation_id, tenant_id, email, role, code_sha256,"
            " invited_by, created_at, expires_at) VALUES (gen_random_uuid(), 'larkfield',"
            " 'tomas@larkfield.example', 'staff', 'x', 'usr-grace', now(), now() - interval"
            " '1 day')"
        )
