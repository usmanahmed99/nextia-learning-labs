"""Where does one customer's personal data live? A small inventory for the privacy work.

It lists every place a customer's data sits in this practice system, so that a deletion can reach all
of them. Some places are in the database; some are files; one is outside the system (the model
provider that saw the prompt). The count is a teaching tool, not a legal record.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .data import VFS


def copies(db: Path, customer_id: str) -> list[dict]:
    """Every place this customer's data lives, with a short reason and whether a deletion reaches it."""
    out = []
    with closing(sqlite3.connect(db)) as con:
        con.row_factory = sqlite3.Row
        cust = con.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone()
        if cust is None:
            return out
        out.append({"where": "database: customers", "what": "name, e-mail, phone, city", "count": 1,
                    "deletable": True})
        for table, what in (("orders", "orders and totals"), ("tickets", "the customer's messages")):
            n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE customer_id=?", (customer_id,)).fetchone()[0]
            if n:
                out.append({"where": f"database: {table}", "what": what, "count": n, "deletable": True})
        order_ids = [r[0] for r in con.execute("SELECT order_id FROM orders WHERE customer_id=?", (customer_id,))]
        tickets = [r[0] for r in con.execute("SELECT ticket_id FROM tickets WHERE customer_id=?", (customer_id,))]
        for table, what in (("refunds", "refunds"), ("return_labels", "return labels"), ("emails", "e-mails sent")):
            if not order_ids:
                continue
            marks = ",".join("?" * len(order_ids))
            try:
                n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE order_id IN ({marks})", order_ids).fetchone()[0]
            except sqlite3.OperationalError:
                n = 0
            if n:
                out.append({"where": f"database: {table}", "what": what, "count": n, "deletable": True})
    files = 0
    for tid in tickets:
        for tenant_dir in (VFS / "files").glob("*"):
            folder = tenant_dir / tid
            if folder.is_dir():
                files += len(list(folder.glob("*")))
    if files:
        out.append({"where": "files: attachments", "what": "files the customer attached", "count": files,
                    "deletable": True})
    out.append({"where": "audit log", "what": "actor, action and result (no message bodies when redacted)",
                "count": len(tickets), "deletable": True})
    out.append({"where": "model provider", "what": "the prompt text sent for each reply (outside this system)",
                "count": len(tickets), "deletable": False})
    out.append({"where": "backups", "what": "a copy of the database, kept for recovery", "count": 1,
                "deletable": False})
    return out


def summary(db: Path, customer_id: str) -> dict:
    rows = copies(db, customer_id)
    return {"customer": customer_id, "places": len(rows), "total_copies": sum(r["count"] for r in rows),
            "not_reached_by_a_delete": [r["where"] for r in rows if not r["deletable"]], "rows": rows}
