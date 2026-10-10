"""Larkfield's order, payment, shipping and ticket systems: a mock, in a local SQLite file.

Nothing here reaches a real system. Every write is a mock write into your practice database
(work/larkfield.sqlite, a copy of data/larkfield.sqlite; `python -m resolver reset` makes a fresh copy).

The services behave like real ones in the ways that matter for this course:
- reads return facts (and compute the dates, so that no model has to);
- writes take an operation ID: the same ID twice returns the first result and changes nothing more
  (the service is idempotent); `operation(op_id)` tells whether an operation happened (reconciliation);
- failures can be injected per task (simulated): a timeout, a service that is down (503), a refusal,
  and the worst one, a timeout AFTER the write: the change happened, but the caller does not know.
"""

import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from .data import SEED_DB, TODAY, WORK, load_passages
from .dates import add_business_days, business_days_between

PRACTICE_DB = WORK / "larkfield.sqlite"
RETURN_FEE = 12.95
WRITE_TABLES = {"create_return_label": "return_labels", "reship_item": "reshipments",
                "request_refund": "refunds", "add_ticket_note": "ticket_notes"}


class ServiceError(Exception):
    """A service failed. `code` is one of: timeout, unavailable, denied, invalid."""
    code = "error"


class ServiceTimeout(ServiceError):
    code = "timeout"


class ServiceUnavailable(ServiceError):
    code = "unavailable"


class PermissionDenied(ServiceError):
    code = "denied"


class InvalidRequest(ServiceError):
    code = "invalid"


class Faults:
    """Simulated failures for one task: [{"tool": ..., "mode": ..., "times": n}] (times 99 = always).

    Modes: timeout and unavailable (any tool, before it does anything), denied (a write is refused),
    timeout_before_write and timeout_after_write (a write: the second one changes the data, then times out).
    """

    def __init__(self, specs: list[dict] | None = None):
        self.left = {(s["tool"], s["mode"]): s.get("times", 1) for s in specs or []}
        self.seen: list[tuple[str, str]] = []

    def take(self, tool: str, modes: tuple[str, ...]) -> str | None:
        for mode in modes:
            if self.left.get((tool, mode), 0) > 0:
                self.left[(tool, mode)] -= 1
                self.seen.append((tool, mode))
                return mode
        return None


def reset_practice_db(path: Path | None = None) -> Path:
    path = path or PRACTICE_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SEED_DB, path)
    return path


def short(op_id: str) -> str:
    """A short, stable record ID from an operation ID."""
    return hashlib.sha256(op_id.encode()).hexdigest()[:8].upper()


def _d(text: str | None) -> date | None:
    return date.fromisoformat(text) if text else None


class World:
    """The services, over one practice database. `ticket_id` is written on every change."""

    def __init__(self, path: Path | None = None, ticket_id: str = "", faults: Faults | None = None,
                 today: date = TODAY):
        path = path or PRACTICE_DB
        if not path.exists():
            reset_practice_db(path)
        self.path = path
        self.ticket_id = ticket_id
        self.faults = faults or Faults()
        self.today = today
        self._passages = None

    def _db(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _fail_before(self, tool: str, write: bool = False) -> None:
        mode = self.faults.take(tool, ("timeout", "unavailable", "timeout_before_write") + (("denied",) if write else ()))
        if mode in ("timeout", "timeout_before_write"):
            raise ServiceTimeout(f"{tool}: no answer within 10 seconds (simulated)")
        if mode == "unavailable":
            raise ServiceUnavailable(f"{tool}: HTTP 503 Service Unavailable (simulated)")
        if mode == "denied":
            raise PermissionDenied(f"{tool}: the warehouse system refused the request: order on hold (simulated)")

    # ---------------------------------------------------------------- reads
    def order(self, order_id: str) -> dict | None:
        """One order with its items, boxes, refunds and return labels, and the dates computed."""
        self._fail_before("get_order")
        with closing(self._db()) as db:
            o = db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if o is None:
                return None
            out = dict(o)
            del out["customer_id"]                   # the tools already know whose ticket it is
            out["gift_message"] = out.pop("note")    # written by the buyer at checkout: data, not instructions
            out["items"] = [
                {"sku": r["sku"], "product": r["product"], "quantity": r["quantity"], "unit_price": r["unit_price"],
                 "box": r["box"], "in_stock": r["stock"] > 0, "change_of_mind_return": bool(r["change_of_mind_return"])}
                for r in db.execute("SELECT i.*, p.stock, p.change_of_mind_return FROM order_items i JOIN products p "
                                    "USING(sku) WHERE order_id = ? ORDER BY box, sku", (order_id,))]
            out["boxes"] = []
            for s in db.execute("SELECT * FROM shipments WHERE order_id = ? ORDER BY box", (order_id,)):
                box = {"box": s["box"], "status": s["status"], "shipped_on": s["shipped_on"],
                       "delivered_on": s["delivered_on"], "last_scan_on": s["last_scan_on"],
                       "courier_note": s["courier_note"]}
                if s["shipped_on"]:
                    expected = add_business_days(_d(s["shipped_on"]), 5)
                    box["expected_by"] = expected.isoformat()
                    if not s["delivered_on"]:
                        box["business_days_late"] = business_days_between(expected, self.today)
                    else:
                        box["business_days_since_delivery"] = business_days_between(_d(s["delivered_on"]), self.today)
                out["boxes"].append(box)
            if o["shipped_on"]:
                out["expected_by"] = add_business_days(_d(o["shipped_on"]), 5).isoformat()
            if o["delivered_on"]:
                out["days_since_delivery"] = (self.today - _d(o["delivered_on"])).days
            elif o["shipped_on"]:
                out["business_days_late"] = business_days_between(_d(out["expected_by"]), self.today)
            out["refunds"] = [{"amount": r["amount"], "reason_code": r["reason_code"], "created_at": r["created_at"][:10]}
                              for r in db.execute("SELECT * FROM refunds WHERE order_id = ? ORDER BY created_at",
                                                  (order_id,))]
            out["return_labels"] = [{"sku": r["sku"], "reason": r["reason"], "created_at": r["created_at"][:10]}
                                    for r in db.execute("SELECT * FROM return_labels WHERE order_id = ? "
                                                        "ORDER BY created_at", (order_id,))]
            out["reshipments"] = [{"sku": r["sku"], "quantity": r["quantity"], "created_at": r["created_at"][:10]}
                                  for r in db.execute("SELECT * FROM reshipments WHERE order_id = ? ORDER BY created_at",
                                                      (order_id,))]
            return out

    def customer_orders(self, customer_id: str) -> list[dict]:
        self._fail_before("get_customer_orders")
        with closing(self._db()) as db:
            rows = db.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY ordered_on DESC", (customer_id,))
            out = []
            for o in rows.fetchall():
                products = [r["product"] for r in db.execute("SELECT product FROM order_items WHERE order_id = ? "
                                                             "ORDER BY box, sku", (o["order_id"],))]
                out.append({"order_id": o["order_id"], "status": o["status"], "ordered_on": o["ordered_on"],
                            "delivered_on": o["delivered_on"], "products": products})
            return out

    def owner(self, order_id: str) -> str | None:
        """Who owns an order (used by the permission checks; never shown to the model)."""
        with closing(self._db()) as db:
            row = db.execute("SELECT customer_id FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            return row["customer_id"] if row else None

    def payments(self, order_id: str) -> dict:
        self._fail_before("get_payments")
        with closing(self._db()) as db:
            pays = [dict(r) for r in db.execute("SELECT payment_id, kind, amount, status, created_on FROM payments "
                                                "WHERE order_id = ? ORDER BY payment_id", (order_id,))]
            refunds = [dict(r) for r in db.execute("SELECT payment_id, amount, reason_code, created_at FROM refunds "
                                                   "WHERE order_id = ? ORDER BY created_at", (order_id,))]
        return {"payments": pays, "refunds": [{**r, "created_at": r["created_at"][:10]} for r in refunds]}

    def search_policy(self, query: str, k: int = 3) -> list[dict]:
        """Keyword search (SQLite FTS5, BM25) over the policy passages; the top k."""
        self._fail_before("search_policy")
        if self._passages is None:
            self._passages = load_passages()
        con = sqlite3.connect(":memory:")
        con.execute("CREATE VIRTUAL TABLE p USING fts5(passage_id UNINDEXED, title, section, text, "
                    "tokenize='unicode61 remove_diacritics 2')")
        con.executemany("INSERT INTO p VALUES (?,?,?,?)",
                        [(p["passage_id"], p["title"], p["section"], p["text"]) for p in self._passages])
        words = [w for w in "".join(c if c.isalnum() else " " for c in query.lower()).split() if len(w) > 2]
        if not words:
            return []
        q = " OR ".join(f'"{w}"' for w in words)
        ids = [r[0] for r in con.execute("SELECT passage_id FROM p WHERE p MATCH ? ORDER BY bm25(p), passage_id "
                                         "LIMIT ?", (q, k))]
        con.close()
        by_id = {p["passage_id"]: p for p in self._passages}
        return [{key: by_id[i][key] for key in ("passage_id", "title", "version", "effective_from", "effective_to",
                                                 "section", "text")} for i in ids]

    # ---------------------------------------------------------------- writes
    def operation(self, op_id: str) -> dict | None:
        """Reconciliation: did the operation with this ID happen? Its stored result, or None."""
        with closing(self._db()) as db:
            row = db.execute("SELECT * FROM operations WHERE op_id = ?", (op_id,)).fetchone()
            return json.loads(row["result"]) if row else None

    def _write(self, tool: str, op_id: str, arguments: dict, apply) -> dict:
        self._fail_before(tool, write=True)
        with closing(self._db()) as db:
            done = db.execute("SELECT result FROM operations WHERE op_id = ?", (op_id,)).fetchone()
            if done:  # idempotent: the same operation ID again changes nothing
                return {**json.loads(done["result"]), "repeated": True}
            now = datetime.now().isoformat(timespec="seconds")
            result = apply(db, now)
            db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?)",
                       (op_id, tool, json.dumps(arguments, sort_keys=True), self.ticket_id, json.dumps(result), now))
            db.commit()
        if self.faults.take(tool, ("timeout_after_write",)):
            raise ServiceTimeout(f"{tool}: no answer within 10 seconds (simulated; the change WAS made)")
        return result

    def _order_row(self, db, order_id: str):
        o = db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if o is None:
            raise InvalidRequest(f"no order {order_id}")
        return o

    def _item(self, db, order_id: str, sku: str):
        item = db.execute("SELECT i.*, p.stock FROM order_items i JOIN products p USING(sku) "
                          "WHERE order_id = ? AND sku = ?", (order_id, sku)).fetchone()
        if item is None:
            raise InvalidRequest(f"order {order_id} has no item {sku}")
        return item

    def create_return_label(self, op_id: str, order_id: str, sku: str, reason: str) -> dict:
        def apply(db, now):
            o = self._order_row(db, order_id)
            self._item(db, order_id, sku)
            if not o["delivered_on"]:
                raise InvalidRequest(f"order {order_id} is not delivered")
            fee = 0.0 if reason in ("damaged", "wrong_item") else RETURN_FEE
            label_id = f"RL-{short(op_id)}"
            db.execute("INSERT INTO return_labels VALUES (?,?,?,?,?,?,?,?)",
                       (label_id, op_id, order_id, sku, reason, fee, self.ticket_id, now))
            return {"label_id": label_id, "order_id": order_id, "sku": sku, "reason": reason, "fee": fee}
        return self._write("create_return_label", op_id, {"order_id": order_id, "sku": sku, "reason": reason}, apply)

    def reship_item(self, op_id: str, order_id: str, sku: str, quantity: int) -> dict:
        def apply(db, now):
            self._order_row(db, order_id)
            item = self._item(db, order_id, sku)
            if quantity > item["quantity"]:
                raise InvalidRequest(f"order {order_id} has only {item['quantity']} of {sku}")
            if item["stock"] < quantity:
                raise InvalidRequest(f"{sku} is out of stock")
            reship_id = f"RS-{short(op_id)}"
            db.execute("INSERT INTO reshipments VALUES (?,?,?,?,?,?,?)",
                       (reship_id, op_id, order_id, sku, quantity, self.ticket_id, now))
            db.execute("UPDATE products SET stock = stock - ? WHERE sku = ?", (quantity, sku))
            return {"reship_id": reship_id, "order_id": order_id, "sku": sku, "quantity": quantity}
        return self._write("reship_item", op_id, {"order_id": order_id, "sku": sku, "quantity": quantity}, apply)

    def request_refund(self, op_id: str, order_id: str, amount: float, reason_code: str,
                       payment_id: str | None = None) -> dict:
        def apply(db, now):
            o = self._order_row(db, order_id)
            captured = sum(r["amount"] for r in db.execute(
                "SELECT amount FROM payments WHERE order_id = ? AND kind = 'charge' AND status IN ('captured','refunded')",
                (order_id,)))
            refunded = sum(r["amount"] for r in db.execute("SELECT amount FROM refunds WHERE order_id = ?", (order_id,)))
            if amount <= 0 or round(amount, 2) > round(captured - refunded, 2):
                raise InvalidRequest(f"refund {amount:.2f} is more than the {captured - refunded:.2f} left to refund "
                                     f"on {order_id}")
            if payment_id:
                pay = db.execute("SELECT * FROM payments WHERE payment_id = ? AND order_id = ?",
                                 (payment_id, order_id)).fetchone()
                if pay is None or pay["kind"] != "charge" or pay["status"] != "captured":
                    raise InvalidRequest(f"{payment_id} is not a captured charge of {order_id}")
                db.execute("UPDATE payments SET status = 'refunded' WHERE payment_id = ?", (payment_id,))
            refund_id = f"RF-{short(op_id)}"
            db.execute("INSERT INTO refunds VALUES (?,?,?,?,?,?,?,?)",
                       (refund_id, op_id, order_id, payment_id, round(amount, 2), reason_code, self.ticket_id, now))
            return {"refund_id": refund_id, "order_id": order_id, "amount": round(amount, 2),
                    "reason_code": reason_code, "payment_id": payment_id}
        return self._write("request_refund", op_id, {"order_id": order_id, "amount": round(amount, 2),
                                                     "reason_code": reason_code, "payment_id": payment_id}, apply)

    def add_ticket_note(self, op_id: str, text: str) -> dict:
        def apply(db, now):
            note_id = f"TN-{short(op_id)}"
            db.execute("INSERT INTO ticket_notes VALUES (?,?,?,?,?)", (note_id, op_id, self.ticket_id, text, now))
            return {"note_id": note_id}
        return self._write("add_ticket_note", op_id, {"text": text}, apply)

    def changes(self) -> list[dict]:
        """Every change that is not in the seed data (refunds, labels, reshipments), oldest first."""
        out = []
        with closing(self._db()) as db:
            for tool, table in WRITE_TABLES.items():
                if tool == "add_ticket_note":
                    continue
                for r in db.execute(f"SELECT * FROM {table} WHERE op_id NOT LIKE 'seed-%' ORDER BY created_at"):
                    row = dict(r)
                    row["tool"] = tool
                    out.append(row)
        return sorted(out, key=lambda r: r["created_at"])
