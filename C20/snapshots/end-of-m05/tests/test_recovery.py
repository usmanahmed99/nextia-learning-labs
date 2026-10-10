"""Module 5, lesson 3: delete a customer's data everywhere, and find what a partial failure left."""

import pytest

from scripts import erase_customer, scan
from scripts.load import DATA
from ticket_api.files import LocalFileStore


@pytest.fixture
def store(tmp_path):
    """The small data's files in a local store (as Azurite would have them)."""
    s = LocalFileStore(tmp_path / "files")
    for p in (DATA / "small" / "files").rglob("*"):
        if p.is_file():
            s.put(p.relative_to(DATA / "small" / "files").as_posix(), p.read_bytes(), "")
    return s


def customer_with_files(conn):
    return conn.execute(
        "SELECT t.customer_id FROM attachments a JOIN tickets t USING (ticket_id)"
        " GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT 1"
    ).fetchone()["customer_id"]


def test_the_small_data_is_consistent(conn, store):
    report = scan.scan(conn, store)
    for key in (
        "orphan_files",
        "missing_files",
        "waiting_deletions",
        "old_pending_uploads",
        "stale_vectors",
    ):
        assert report[key] == [], key
    assert report["tickets_without_current_vector"] == 0


def test_erasure_reaches_rows_files_and_vectors(conn, store):
    customer = customer_with_files(conn)
    keys = [
        r["object_key"]
        for r in conn.execute(
            "SELECT object_key FROM attachments JOIN tickets USING (ticket_id) WHERE"
            " customer_id = %s",
            (customer,),
        )
    ]
    tickets = [
        r["ticket_id"]
        for r in conn.execute("SELECT ticket_id FROM tickets WHERE customer_id = %s", (customer,))
    ]
    runs = conn.execute(
        "SELECT count(*) AS n FROM ai_runs WHERE ticket_id = ANY(%s)", (tickets,)
    ).fetchone()["n"]
    counts = erase_customer.erase_in_database(conn, customer)
    erase_customer.finish(conn, store)
    assert counts["files"] == len(keys) > 0
    assert all(store.size(k) is None for k in keys)
    for table in ("tickets", "customers"):
        assert (
            conn.execute(
                f"SELECT count(*) AS n FROM {table} WHERE customer_id = %s", (customer,)
            ).fetchone()["n"]
            == 0
        )
    for table in ("messages", "ticket_embeddings", "attachments", "ai_runs"):
        assert (
            conn.execute(
                f"SELECT count(*) AS n FROM {table} WHERE ticket_id = ANY(%s)", (tickets,)
            ).fetchone()["n"]
            == 0
        )
    kept = conn.execute(
        "SELECT count(*) AS n FROM ai_runs WHERE ticket_id IS NULL AND output IS NULL"
    ).fetchone()
    assert kept["n"] == runs  # the costs stay, with no ticket and no text
    assert scan.scan(conn, store)["orphan_files"] == []


def test_a_crash_after_the_database_step_leaves_files_that_the_scan_finds(conn, store):
    customer = customer_with_files(conn)
    counts = erase_customer.erase_in_database(conn, customer)  # then the program stops (no finish)
    report = scan.scan(conn, store)
    assert len(report["waiting_deletions"]) == counts["files"]
    assert report["orphan_files"] == []  # the outbox knows these files: they are not unknown
    erase_customer.finish(conn, store)
    assert scan.scan(conn, store)["waiting_deletions"] == []


def test_a_file_that_nobody_knows_is_an_orphan(conn, store):
    store.put("tickets/T-30001/unknown/photo-9.png", b"x", "image/png")
    assert scan.scan(conn, store)["orphan_files"] == ["tickets/T-30001/unknown/photo-9.png"]


def test_a_missing_file_is_found(conn, store):
    key = conn.execute("SELECT object_key FROM attachments LIMIT 1").fetchone()["object_key"]
    store.delete(key)
    assert scan.scan(conn, store)["missing_files"] == [key]


def test_a_changed_ticket_text_makes_its_vector_stale(conn, store):
    conn.execute("UPDATE tickets SET body = body || ' (edited)' WHERE ticket_id = 'T-30002'")
    assert scan.scan(conn, store)["stale_vectors"] == ["T-30002"]


def test_a_file_deleted_before_waits_again_after_a_restore(conn, store):
    """A restored backup brings back rows (and the files may still be there): erasing again
    must delete them again, although file_deletions says they were deleted once."""
    customer = customer_with_files(conn)
    keys = [
        r["object_key"]
        for r in conn.execute(
            "SELECT object_key FROM attachments JOIN tickets USING (ticket_id)"
            " WHERE customer_id = %s",
            (customer,),
        )
    ]
    for key in keys:  # as if an earlier erasure had finished before the backup was restored
        conn.execute(
            "INSERT INTO file_deletions (object_key, reason, deleted_at)"
            " VALUES (%s, 'earlier', now())",
            (key,),
        )
    erase_customer.erase_in_database(conn, customer)
    assert sorted(scan.scan(conn, store)["waiting_deletions"]) == sorted(keys)
