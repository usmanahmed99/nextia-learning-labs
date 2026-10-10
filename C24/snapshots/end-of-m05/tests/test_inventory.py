"""The privacy inventory finds every place a customer's data lives, and marks the copies a delete
cannot reach."""

from support_assistant.inventory import summary
from support_assistant.runner import fresh_world


def test_inventory_lists_database_files_and_backups():
    s = summary(fresh_world(), "C-50533")
    wheres = {r["where"] for r in s["rows"]}
    assert {"database: customers", "database: tickets", "files: attachments", "backups"} <= wheres
    assert s["total_copies"] >= s["places"]


def test_a_run_adds_a_stored_conversation_an_audit_trail_and_a_provider_copy():
    import json
    from support_assistant.assistant import run_case
    from support_assistant.data import load_tasks
    from tests.scripted import Scripted
    w = fresh_world(redact_log=False)
    before = summary(w, "C-50533")["total_copies"]
    run_case(load_tasks()["TASK-02"], Scripted([("Sorry about the damage.", [])]).complete, w, "scripted", "start")
    s = summary(w, "C-50533")
    wheres = {r["where"] for r in s["rows"]}
    assert {"database: conversations", "audit log", "model provider"} <= wheres
    assert s["total_copies"] > before
    assert "model provider" in s["not_reached_by_a_delete"] and "backups" in s["not_reached_by_a_delete"]


def test_unknown_customer_has_no_copies():
    assert summary(fresh_world(), "C-00000")["total_copies"] == 0
