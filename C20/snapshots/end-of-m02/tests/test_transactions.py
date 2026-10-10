"""Module 2, lesson 3: a change happens completely or not at all, and no update is lost."""

import psycopg
import pytest

from scripts import lost_update


def test_read_then_write_loses_an_update(db_url):
    result = lost_update.run(db_url, "read-then-write")
    assert result["lost_updates"] == 1


@pytest.mark.parametrize("mode", ["lock", "atomic"])
def test_a_row_lock_or_one_update_statement_loses_nothing(db_url, mode):
    result = lost_update.run(db_url, mode)
    assert result["lost_updates"] == 0
    assert result["end"] == result["expected"]


def test_a_failed_transaction_changes_nothing(db_url):
    with psycopg.connect(db_url) as conn:
        count = "SELECT message_count FROM tickets WHERE ticket_id = 'T-30002'"
        before = conn.execute(count).fetchone()
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                conn.execute(
                    "INSERT INTO messages (ticket_id, author, body)"
                    " VALUES ('T-30002', 'agent', 'First part')"
                )
                conn.execute(
                    "UPDATE tickets SET message_count = message_count + 1"
                    " WHERE ticket_id = 'T-30002'"
                )
                conn.execute(
                    "INSERT INTO messages (ticket_id, author, body)"
                    " VALUES ('T-30002', 'robot', 'x')"
                )
        after = conn.execute(count).fetchone()
        n = conn.execute("SELECT count(*) FROM messages WHERE body = 'First part'").fetchone()[0]
    assert after == before
    assert n == 0
