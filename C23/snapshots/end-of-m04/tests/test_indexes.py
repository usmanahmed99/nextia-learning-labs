"""Module 4, lesson 2: the list query can use its index (the index matches the query's shape).

The small data is too small for PostgreSQL to prefer an index (a scan of 200 rows is
cheaper), so the test turns off the alternatives and checks that the index fits."""

import json

from ticket_api import repository


def plan(conn, sql, params):
    with conn.transaction():
        conn.execute("SET LOCAL enable_seqscan = off")
        conn.execute("SET LOCAL enable_bitmapscan = off")
        return json.dumps(
            conn.execute(f"EXPLAIN (FORMAT JSON) {sql}", params).fetchone()["QUERY PLAN"]
        )


def test_the_ticket_list_uses_the_queue_index(conn):
    sql, params = repository.list_query(
        tenant_id="larkfield", status="open", team="billing", limit=20
    )
    text = plan(conn, sql, params)
    # since the authentication course: the index that starts with the organization
    assert "tickets_tenant_queue_idx" in text
    assert '"Node Type": "Sort"' not in text  # the index gives the order: nothing to sort


def test_the_latest_run_uses_its_index(conn):
    sql, params = repository.list_query(
        tenant_id="larkfield", status="open", team="billing", limit=20
    )
    assert "ai_runs_ticket_idx" in plan(conn, sql, params)


def test_the_messages_of_a_ticket_use_their_index(conn):
    text = plan(conn, "SELECT * FROM messages WHERE ticket_id = %(t)s", {"t": "T-30002"})
    assert "messages_ticket_idx" in text
