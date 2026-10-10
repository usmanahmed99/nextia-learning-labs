"""Module 2, lesson 3: a change happens completely or not at all, and no update is lost."""

import psycopg
import pytest

from scripts import lost_update
from ticket_api import repository


def test_read_then_write_loses_an_update(db_url):
    result = lost_update.run(db_url, "read-then-write")
    assert result["lost_updates"] == 1


@pytest.mark.parametrize("mode", ["lock", "atomic"])
def test_a_row_lock_or_one_update_statement_loses_nothing(db_url, mode):
    result = lost_update.run(db_url, mode)
    assert result["lost_updates"] == 0
    assert result["end"] == result["expected"]


def test_a_failed_transaction_changes_nothing(db_url):
    with psycopg.connect(db_url, row_factory=psycopg.rows.dict_row) as conn:
        before = conn.execute(
            "SELECT message_count FROM tickets WHERE ticket_id = 'T-30002'"
        ).fetchone()
        with pytest.raises(psycopg.errors.CheckViolation):
            with conn.transaction():
                repository.add_message(conn, "T-30002", "agent", "First part")
                conn.execute(
                    "INSERT INTO messages (ticket_id, author, body) VALUES ('T-30002',"
                    " 'robot', 'x')"
                )
        after = conn.execute(
            "SELECT message_count FROM tickets WHERE ticket_id = 'T-30002'"
        ).fetchone()
        n = conn.execute("SELECT count(*) AS n FROM messages WHERE body = 'First part'").fetchone()[
            "n"
        ]
    assert after == before
    assert n == 0


def test_two_messages_at_the_same_time_are_both_counted(api):
    import threading

    before = api.get("/v1/tickets/T-30002").json()["message_count"]
    threads = [
        threading.Thread(
            target=api.post,
            args=("/v1/tickets/T-30002/messages",),
            kwargs={"json": {"author": "agent", "body": f"Reply {i}"}},
        )
        for i in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ticket = api.get("/v1/tickets/T-30002").json()
    assert ticket["message_count"] == before + 5
    assert len(ticket["messages"]) == before + 5
