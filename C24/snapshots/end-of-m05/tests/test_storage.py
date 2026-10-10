"""Minimized storage, retention and deletion: keep less, delete on time, and forget one customer
everywhere this system reaches (and say honestly where it cannot)."""

from datetime import timedelta

from support_assistant.assistant import run_case
from support_assistant.data import TODAY, load_tasks
from support_assistant.inventory import summary
from support_assistant.runner import fresh_world
from support_assistant.storage import RETENTION_DAYS, forget, mask, purge
from tests.scripted import Scripted

REPLY = [("Hello Priti, sorry about the damage. We will call you on +1 905 555 0102.", [])]


def _run(design):
    w = fresh_world()
    run_case(load_tasks()["TASK-02"], Scripted(list(REPLY)).complete, w, "scripted", design)
    return w


def test_mask_hides_contact_details_and_the_name():
    out = mask("Priti Shah, priti.shah@mail.example, +1 905 555 0102", ("Priti Shah",))
    assert "Priti" not in out and "@" not in out and "905" not in out


def test_full_storage_keeps_the_text_minimized_storage_does_not():
    full = _run("start").conversations("C-50533")[0]
    small = _run("secure").conversations("C-50533")[0]
    assert full["ticket_text"] and full["customer_email"] and full["expires_on"] is None
    assert small["ticket_text"] is None and small["customer_email"] is None and small["expires_on"]


def test_purge_deletes_only_what_is_past_its_end_date():
    w = _run("secure")
    assert purge(w, TODAY) == 0
    assert purge(w, TODAY + timedelta(days=RETENTION_DAYS + 1)) == 1


def test_forget_reaches_the_database_and_the_files_but_not_the_provider_or_backups():
    w = _run("secure")
    forget(w, "C-50533")
    s = summary(w, "C-50533")
    wheres = {r["where"] for r in s["rows"]}
    assert not {"database: customers", "database: tickets", "database: conversations", "files: attachments"} & wheres
    assert s["not_reached_by_a_delete"] == ["model provider", "backups"]
    assert w.customer("C-50533")["name"] == "[deleted]"
