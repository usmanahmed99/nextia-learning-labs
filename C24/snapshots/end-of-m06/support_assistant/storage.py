"""What the assistant keeps after a run, for how long, and how one customer's data is deleted.

Full storage (the weak start) keeps the whole conversation: the customer's message, the team
member's request, the reply draft, and the customer's name and e-mail address, with no end date.
Minimized storage keeps only what the team needs later: the outcome of the run (the tools used, the
proposals, why it stopped) with the customer's ID, no message text, and an end date
(RETENTION_DAYS). `purge` deletes what is past its end date.

`forget(customer)` deletes or anonymizes one customer's data everywhere this system can reach. It
cannot reach two places, and it says so: the model provider, which received the prompts, and the
backups, which keep a copy until they expire. Orders and refunds are kept for the shop's accounts,
with the free-text notes cleared: how long a shop must keep them is a question for a qualified
reviewer, not for this code.
"""

import json
import re
import shutil
from contextlib import closing
from datetime import date, timedelta

from .data import TODAY

RETENTION_DAYS = 30
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")


def mask(text: str, names: tuple[str, ...] = ()) -> str:
    """Replace e-mail addresses, phone numbers and the given names with markers."""
    text = EMAIL.sub("[e-mail]", text or "")
    text = PHONE.sub("[phone]", text)
    for name in names:
        for part in [name, *name.split()]:
            if len(part) > 2:
                text = re.sub(rf"\b{re.escape(part)}\b", "[name]", text)
    return text


def outcome(state) -> dict:
    """What happened in a run, with no message text."""
    return {"stop": state.stop_reason, "role": state.role,
            "tools": [f"{e.tool}:{'ok' if e.ok else e.code}" for e in state.tool_events],
            "proposals": [{"tool": p.tool, "order_id": p.arguments.get("order_id"),
                           "refused": bool(p.refused_reason), "approval": p.approval_id} for p in state.proposals]}


def save_run(world, state, case, ticket: dict, minimized: bool) -> None:
    """Store one run, fully or minimized."""
    customer = world.customer(ticket["customer_id"]) or {}
    row = {"run_id": state.run_id, "tenant": state.tenant, "case_id": case.case_id, "ticket_id": ticket["ticket_id"],
           "customer_id": ticket["customer_id"], "outcome": json.dumps(outcome(state)),
           "created_at": TODAY.isoformat()}
    if minimized:
        row["expires_on"] = (TODAY + timedelta(days=RETENTION_DAYS)).isoformat()
    else:
        row.update(customer_name=customer.get("name"), customer_email=customer.get("email"), request=case.request,
                   ticket_text=ticket["text"], answer=state.answer)
    world.save_conversation(row)


def minimize_evidence(evidence: dict, customer: dict) -> dict:
    """The approval evidence with the customer's contact details masked (the reviewer needs the rest)."""
    names = tuple(n for n in (customer.get("name"),) if n)
    return {k: (mask(v, names) if k in ("ticket_text", "draft") else v) for k, v in evidence.items()}


def purge(world, today: date | None = None) -> int:
    """Delete the stored conversations that are past their end date. Returns how many were deleted."""
    today = today or TODAY
    with closing(world._con()) as con:
        n = con.execute("DELETE FROM conversations WHERE expires_on IS NOT NULL AND expires_on < ?",
                        (today.isoformat(),)).rowcount
        con.commit()
    return n


def forget(world, customer_id: str) -> dict:
    """Delete or anonymize one customer's data in every place this system reaches. Returns what it did."""
    done: dict[str, int] = {}
    with closing(world._con()) as con:
        tickets = [r[0] for r in con.execute("SELECT ticket_id FROM tickets WHERE customer_id=?", (customer_id,))]
        orders = [r[0] for r in con.execute("SELECT order_id FROM orders WHERE customer_id=?", (customer_id,))]
        to_addr = [r[0] for r in con.execute("SELECT email FROM customers WHERE customer_id=?", (customer_id,))]
        done["conversations deleted"] = con.execute("DELETE FROM conversations WHERE customer_id=?",
                                                    (customer_id,)).rowcount
        done["approvals deleted"] = sum(
            con.execute("DELETE FROM approvals WHERE json_extract(evidence, '$.ticket')=?", (t,)).rowcount
            for t in tickets)
        done["e-mails deleted"] = sum(con.execute("DELETE FROM emails WHERE to_address=?", (a,)).rowcount
                                      for a in to_addr)
        done["tickets deleted"] = con.execute("DELETE FROM tickets WHERE customer_id=?", (customer_id,)).rowcount
        done["order notes cleared"] = con.execute(
            "UPDATE orders SET courier_note=NULL, gift_message=NULL WHERE customer_id=?", (customer_id,)).rowcount
        done["customer anonymized"] = con.execute(
            "UPDATE customers SET name='[deleted]', email='', phone='', city='', note=NULL WHERE customer_id=?",
            (customer_id,)).rowcount
        con.commit()
    files = 0
    for t in tickets:
        for folder in (world.vfs / "files").glob(f"*/{t}"):
            files += sum(1 for _ in folder.glob("*"))
            shutil.rmtree(folder)
    done["attached files deleted"] = files
    done["orders kept for the accounts"] = len(orders)
    world.log("system", "", "forget", "done", customer=customer_id)
    return done
