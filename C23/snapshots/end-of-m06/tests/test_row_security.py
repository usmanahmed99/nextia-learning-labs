"""Module 4, lesson 2: row-level security, the second lock (migrations/017)."""

import psycopg
import pytest

from ticket_api.db import Database


def count(conn, sql="SELECT count(*) AS n FROM tickets"):
    return conn.execute(sql).fetchone()["n"]


def test_a_query_without_the_organization_sees_only_the_transactions_organization(db_url):
    db = Database(db_url, pool=False, row_security=True)
    with db.connection("bramble") as conn:
        assert count(conn) == 40  # the query forgot "WHERE tenant_id": the policy did not
    with db.connection("larkfield") as conn:
        assert count(conn) == 200


def test_without_an_organization_the_app_role_sees_nothing(db_url):
    with psycopg.connect(db_url, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("SET ROLE ticket_app")
        assert count(conn) == 0


def test_a_superuser_is_not_stopped_by_the_policies(db_url):
    """The surprise: the Compose user is a superuser. Setting the organization is not enough;
    the API must also switch to ticket_app."""
    with psycopg.connect(db_url, row_factory=psycopg.rows.dict_row) as conn:
        conn.execute("SELECT set_config('app.tenant_id', 'bramble', false)")
        assert count(conn) == 240


def test_a_write_into_another_organization_is_refused(db_url):
    db = Database(db_url, pool=False, row_security=True)
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match="row-level security"):
        with db.connection("bramble") as conn:
            conn.execute(
                "INSERT INTO messages (tenant_id, ticket_id, author, body)"
                " VALUES ('larkfield', 'T-30002', 'agent', 'x')"
            )


def test_the_settings_end_with_the_transaction(db_url):
    db = Database(db_url, min_size=1, max_size=1, row_security=True)
    db.open()
    try:
        with db.connection("bramble") as conn:
            assert count(conn) == 40
        with db.connection() as conn:  # the same pooled connection, no organization
            row = conn.execute(
                "SELECT current_user AS u, current_setting('app.tenant_id', true) AS t"
            ).fetchone()
            assert row["u"] == "tickets" and row["t"] in ("", None)
    finally:
        db.close()


def test_the_api_works_with_row_security_off_too(make_api):
    api = make_api(user="usr-grace", db_row_security=False)
    assert api.get("/v1/tenants/larkfield/tickets?limit=5").status_code == 200
