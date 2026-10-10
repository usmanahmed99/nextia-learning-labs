"""Module 3, lesson 2: a pool shares a few connections; a failed request never keeps one."""

import pytest

from scripts import pool_demo
from ticket_api.db import Database, DatabaseBusy


def test_a_failed_transaction_leaves_no_partial_update_and_no_connection(db_url):
    result = pool_demo.rollback(db_url)
    assert "violates check constraint" in result["error"]
    assert result["messages_after"] == result["messages_before"]
    assert result["pool_after"]["available"] == result["pool_after"]["size"]


def test_a_failed_api_request_returns_its_connection(make_api):
    api = make_api(db_pool_min=2, db_pool_max=2, db_pool_timeout=1.0)
    for _ in range(5):  # more failures than connections
        response = api.post(
            "/v1/tickets/T-30002/messages", json={"author": "agent", "body": "x" * 6000}
        )
        assert response.status_code == 422
        response = api.get("/v1/tickets/T-99999")
        assert response.status_code == 404
    assert api.get("/v1/tickets?limit=1").status_code == 200
    stats = api.app.state.db.stats()
    assert stats["waiting"] == 0


def test_an_empty_pool_answers_503_busy(make_api):
    api = make_api(db_pool_min=1, db_pool_max=1, db_pool_timeout=0.5)
    db = api.app.state.db
    db.pool.wait()
    held = db.pool.getconn()  # someone holds the only connection
    try:
        response = api.get("/v1/tickets?limit=1")
    finally:
        db.pool.putconn(held)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_busy"
    assert response.headers["Retry-After"] == "2"
    assert api.get("/v1/tickets?limit=1").status_code == 200


def test_a_leak_empties_the_pool(db_url):
    result = pool_demo.leak(db_url, size=2, timeout=0.5)
    assert result["steps"][-1]["result"] == "busy (503)"


def test_requests_wait_for_a_free_connection(db_url):
    result = pool_demo.exhaust(db_url, requests=4, size=2, hold=0.6, timeout=2.0)
    assert [e["outcome"] for e in result["events"]] == ["ok"] * 4


def test_a_database_that_does_not_answer_gives_503(make_api):
    api = make_api(database_url="postgresql://tickets:x@127.0.0.1:1/none", db_pool_timeout=0.5)
    response = api.get("/v1/tickets")
    assert response.status_code == 503
    assert response.json()["error"]["code"] in ("database_busy", "database_unavailable")


def test_without_the_pool_every_request_opens_a_connection(db_url):
    db = Database(db_url, pool=False)
    for _ in range(3):
        with db.connection() as conn:
            conn.execute("SELECT 1")
    assert db.stats() == {"pool": False, "connections_opened": 3}
    with pytest.raises(DatabaseBusy):
        busy = Database(db_url, min_size=1, max_size=1, timeout=0.2)
        busy.open()
        try:
            busy.pool.wait()
            held = busy.pool.getconn()
            with busy.connection():
                pass
        finally:
            busy.pool.putconn(held)
            busy.close()
