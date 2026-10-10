"""The privacy inventory finds every place a customer's data lives, and marks the copies a delete
cannot reach."""

from support_assistant.inventory import summary
from support_assistant.runner import fresh_world


def test_inventory_lists_database_files_and_outside_copies():
    w = fresh_world()
    s = summary(w.db, "C-50533")
    wheres = {r["where"] for r in s["rows"]}
    assert "database: customers" in wheres
    assert "files: attachments" in wheres
    assert "model provider" in wheres and "backups" in wheres
    assert s["total_copies"] >= s["places"]


def test_a_delete_cannot_reach_the_provider_or_backups():
    w = fresh_world()
    s = summary(w.db, "C-50533")
    assert "model provider" in s["not_reached_by_a_delete"]
    assert "backups" in s["not_reached_by_a_delete"]


def test_unknown_customer_has_no_copies():
    w = fresh_world()
    assert summary(w.db, "C-00000")["total_copies"] == 0
