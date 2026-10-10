"""Where does one customer's personal data live? A small inventory for the privacy work.

It lists every place a customer's data sits in this practice system, so that a deletion can reach all
of them. Most places are in the database or the file area, and are counted there. Three are outside
what a delete in this app changes: the audit log (append-only on purpose), the model provider that
received the prompts (counted from the runs in the audit log), and the backups. The count is a
teaching tool, not a legal record.

A copy "holds content" when it has the customer's message text or contact details (name, e-mail,
phone, city, a free-text note). A copy without content can still point to the customer by an ID.
"""

import json
import sqlite3
from contextlib import closing


def copies(world, customer_id: str) -> list[dict]:
    """Every place this customer's data lives: where, what, how many, content or not, and what a delete does."""
    out: list[dict] = []

    def add(where, what, count, content, reach):
        if count:
            out.append({"where": where, "what": what, "count": count, "content": content, "reach": reach})

    with closing(sqlite3.connect(world.db)) as con:
        con.row_factory = sqlite3.Row
        cust = con.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
        if cust is None:
            return out
        if cust["name"] != "[deleted]":
            add("database: customers", "name, e-mail, phone, city", 1, True, "anonymized")
        orders = [dict(r) for r in con.execute("SELECT * FROM orders WHERE customer_id=?", (customer_id,))]
        notes = any(o["courier_note"] or o["gift_message"] for o in orders)
        add("database: orders", "items and totals" + (", delivery or gift notes" if notes else ""), len(orders),
            notes, "kept for the accounts")
        tickets = [r[0] for r in con.execute("SELECT ticket_id FROM tickets WHERE customer_id=?", (customer_id,))]
        add("database: tickets", "the customer's messages", len(tickets), True, "deleted")
        ids = [o["order_id"] for o in orders]
        marks = ",".join("?" * len(ids))
        for table, what in (("refunds", "refund amounts"), ("return_labels", "return labels")):
            n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE order_id IN ({marks})", ids).fetchone()[0] if ids else 0
            add(f"database: {table}", what, n, False, "kept for the accounts")
        n = con.execute("SELECT COUNT(*) FROM emails WHERE to_address=?", (cust["email"],)).fetchone()[0]
        add("database: emails", "e-mails sent to the customer", n, True, "deleted")
        convs = [dict(r) for r in con.execute("SELECT * FROM conversations WHERE customer_id=?", (customer_id,))]
        full = sum(1 for c in convs if c["ticket_text"] or c["customer_email"])
        add("database: conversations", "stored runs with the message, the draft, the name and e-mail", full, True,
            "deleted")
        add("database: conversations", "stored runs, outcome only, with an end date", len(convs) - full, False,
            "deleted")
        # Approvals of this customer's tickets (whatever their order IDs).
        appr = [json.loads(r[0]) for r in con.execute("SELECT evidence FROM approvals")]
        appr = [e for e in appr if e.get("ticket") in tickets]
        add("database: approvals", "proposals and their evidence", len(appr),
            any(e.get("ticket_text") or e.get("draft") for e in appr), "deleted")
        # The audit log: every event of a run for this customer (the run event names the customer by ID).
        runs = {r["run_id"] for r in con.execute("SELECT run_id, detail FROM audit_log WHERE action='assistant'")
                if json.loads(r["detail"]).get("customer") == customer_id}
        events = [dict(r) for r in con.execute("SELECT run_id, detail FROM audit_log")] if runs else []
        events = [e for e in events if e["run_id"] in runs]
        raw = any("message" in json.loads(e["detail"]) for e in events)
        add("audit log", "who did what, when" + (", with the message text" if raw else ", no message text"),
            len(events), raw, "kept: append-only")
        add("model provider", "the prompts sent in each run, outside this system", len(runs), True, "not reached")
    files = sum(len(list(folder.glob("*"))) for t in tickets for folder in (world.vfs / "files").glob(f"*/{t}"))
    add("files: attachments", "files the customer attached", files, True, "deleted")
    add("backups", "a copy of the database, kept for recovery", 1, True, "not reached")
    return out


def summary(world, customer_id: str) -> dict:
    rows = copies(world, customer_id)
    return {"customer": customer_id, "places": len({r["where"] for r in rows}),
            "total_copies": sum(r["count"] for r in rows),
            "content_copies": sum(r["count"] for r in rows if r["content"]),
            "not_reached_by_a_delete": [r["where"] for r in rows if r["reach"] == "not reached"],
            "rows": rows}


def compare(customer_id: str, design: str = "secure") -> list[tuple[str, dict]]:
    """The same customer with full and with minimized storage, then after the end date, then after forget.

    Each storage choice starts from a fresh copy of the data and runs, once, every recorded case on
    this customer's tickets with the design (replayed from the recordings: no account needed).
    """
    from dataclasses import replace
    from datetime import timedelta

    from .assistant import run_case
    from .config import Settings, make_provider
    from .data import TODAY, all_cases
    from .designs import controls_for
    from .runner import fresh_world
    from .storage import RETENTION_DAYS, forget, purge

    settings = Settings.from_env()
    complete = make_provider(settings).complete
    base = controls_for(design)
    out = []
    for label, minimized in (("full storage", False), ("minimized storage", True)):
        world = fresh_world(redact_log=base.redact_logs)
        with closing(sqlite3.connect(world.db)) as con:
            tickets = {r[0] for r in con.execute("SELECT ticket_id FROM tickets WHERE customer_id=?", (customer_id,))}
        for case in all_cases().values():
            if case.ticket_id in tickets:
                run_case(case, complete, world, settings.model, design,
                         controls=replace(base, minimize_data=minimized))
        out.append((label, summary(world, customer_id)))
        if minimized:
            purge(world, TODAY + timedelta(days=RETENTION_DAYS + 1))
            out.append((f"{RETENTION_DAYS + 1} days later", summary(world, customer_id)))
            forget(world, customer_id)
            out.append((f"after forget", summary(world, customer_id)))
    return out
