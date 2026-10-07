"""Tests with a real PostgreSQL database. They run only when TEST_DATABASE_URL
is set: the CI pipeline starts a database for them. Each test starts from an
empty database."""

import os

import psycopg
import pytest

from ticket_api import migrate
from ticket_api.history import History

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL is not set")

RESULT = {
    "category": "billing",
    "priority": 1,
    "confidence": 0.7,
    "score": 0.7,
    "model_version": "keywords-1.0",
}


@pytest.fixture
def database(monkeypatch):
    with psycopg.connect(URL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS classifications, schema_migrations")
    monkeypatch.setenv("DATABASE_URL", URL)
    monkeypatch.delenv("DATABASE_URL_FILE", raising=False)
    return URL


def test_migrations_apply_once(database, capsys):
    assert migrate.main([]) == 0
    assert migrate.main([]) == 0
    out = capsys.readouterr().out
    assert out.count("applied  002_add_score") == 1
    assert "Database is up to date (2 migrations)." in out


def test_history_round_trip(database):
    migrate.main([])
    history = History(database)
    history.add("abc123", RESULT)
    [row] = history.recent(10)
    assert row["category"] == "billing"
    assert row["score"] == pytest.approx(0.7)
