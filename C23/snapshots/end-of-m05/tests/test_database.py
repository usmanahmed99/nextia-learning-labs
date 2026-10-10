"""Tests with a real PostgreSQL database (TEST_DATABASE_URL). They are skipped when
it is not set or PostgreSQL is not running. Each test gets its own fresh database."""

import pytest

from ticket_api import migrate


def test_migrations_apply_once(empty_db_url, capsys):
    assert migrate.main([], url=empty_db_url) == 0
    assert migrate.main([], url=empty_db_url) == 0
    out = capsys.readouterr().out
    assert out.count("applied  002_add_score") == 1
    count = len(list(migrate.MIGRATIONS.glob("*.sql")))
    assert f"Database is up to date ({count} migrations)." in out


def test_history_round_trip(api):
    api.post("/v1/classify", json={"subject": "Refund please", "body": "I was charged twice."})
    [row] = api.get("/v1/history").json()["items"]
    assert row["category"] == "billing"
    assert row["score"] == pytest.approx(0.9)


def test_history_reads_rows_from_version_1_1(api, conn):
    """Version 1.1.0 writes no score. 1.2.0 failed with 500 on such rows."""
    conn.execute(
        "INSERT INTO classifications"
        " (request_id, category, priority, confidence, model_version)"
        " VALUES ('old111', 'shipping', 1, 0.7, 'keywords-1.0')"
    )
    [row] = api.get("/v1/history").json()["items"]
    assert row["score"] == pytest.approx(0.7)
