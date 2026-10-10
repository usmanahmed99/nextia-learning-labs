"""Check every expected outcome in tasks.jsonl against Grace's rules applied in code.

    python reference/c10/data/check_labels.py [DATA_DIR]

The course author labelled each task by reading the ticket and applying policy.md. This script
holds the course author's reading of each ticket (READING: what the customer asks, which order, which item, whether a
photo is attached, what the customer prefers, or which H rule applies) and applies the date and
amount rules (W1-W8) to the practice database. It must agree with every label; it prints each
disagreement. It does not read the ticket text: the reading is a person's.
"""

import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TODAY = date(2026, 10, 9)
HOLIDAYS = {date(2026, 9, 7), date(2026, 10, 12)}

# task -> (intent, order_id, sku or None, details). Intents: status, late, lost, return, damaged, wrong,
# double, refund_eta, missing_box, person:<rule>, outside, find:<intent> (no order ID: the order is found
# from the customer's orders by its product), ambiguous.
READING = {
    "T-80008": ("status", "LK-581106", None, {}), "T-80005": ("status", "LK-266415", None, {}),
    "T-90101": ("return", "LK-640218", "RUG-W", {"used": False}),
    "T-90102": ("damaged", "LK-640327", "CAN-10", {"photo": True}),
    "T-90103": ("damaged", "LK-640436", "PLANTER", {"photo": True}),
    "T-64872": ("double", "LK-739156", None, {}), "T-65273": ("double", "LK-507862", None, {}),
    "T-90104": ("late", "LK-793996", None, {}), "T-64715": ("outside", None, None, {}),
    "T-64789": ("outside", None, None, {}), "T-65001": ("outside", None, None, {"return_status": True}),
    "T-80009": ("status", "LK-551906", None, {}), "T-65070": ("status", "LK-371548", None, {}),
    "T-90105": ("return", "LK-640545", "SOIL-40", {"used": True}),
    "T-90106": ("wrong", "LK-640654", "HOSE-25", {"photo": True}),
    "T-90107": ("refund_eta", "LK-179785", None, {}),
    "T-90201": ("late", "LK-640763", None, {"also_status": "LK-640872"}),
    "T-90202": ("missing_box", "LK-640981", None, {}), "T-90203": ("missing_box", "LK-641090", None, {}),
    "T-64811": ("double", "LK-889023", None, {}),
    "T-90204": ("damaged", "LK-641199", "LADDER-3", {"photo": True}),
    "T-90205": ("damaged", "LK-641210", "FEEDER", {"photo": True}),
    "T-90206": ("find:damaged", "parasol", "PARASOL", {"photo": True}),
    "T-90207": ("find:damaged", "garden chair", "CHAIR-G", {"photo": True}),
    "T-64917": ("damaged", "LK-774120", "CPOLE", {"photo": False}),
    "T-90208": ("late", "LK-641765", None, {}), "T-90209": ("double", "LK-641876", None, {}),
    "T-80004": ("person:H1", None, None, {}), "T-90301": ("person:H1", None, None, {}),
    "T-90302": ("person:H1", None, None, {}), "T-80007": ("person:H2", None, None, {}),
    "T-90303": ("person:H2", None, None, {}), "T-80003": ("person:H3", None, None, {}),
    "T-90304": ("person:H3", None, None, {}), "T-80006": ("person:H5", None, None, {}),
    "T-90305": ("person:H5", None, None, {}), "T-90306": ("person:H1", None, None, {}),
    "T-90401": ("return", "LK-643001", "LIGHTS-6", {"used": False}),
    "T-90402": ("return", "LK-643112", "RUG-W", {"used": False}),
    "T-90403": ("return", "LK-643223", "COMPOST", {"used": False}),
    "T-90404": ("damaged", "LK-643334", "CUSH-4", {"photo": True}),
    "T-90405": ("damaged", "LK-643445", "LADDER-3", {"photo": True}),
    "T-90406": ("late", "LK-643556", None, {}), "T-90407": ("lost", "LK-347101", None, {"prefers": "reship"}),
    "T-90408": ("lost", "LK-643667", None, {"prefers": "refund"}),
    "T-90409": ("return", "LK-643778", "HT-C20", {"used": True}),
    "T-80002": ("person:H4", None, None, {}), "T-80001": ("person:H4", None, None, {}),
    "T-90501": ("late", "LK-644001", None, {}), "T-64856": ("outside", None, None, {"warranty": True}),
    "T-90502": ("person:H3", None, None, {}), "T-90503": ("person:H4", None, None, {}),
    "T-90504": ("damaged", "LK-644445", "POT-TC3", {"photo": True}),
    "T-90505": ("person:H4", None, None, {}),
    "T-90601": ("status", "LK-645001", None, {}), "T-90602": ("double", "LK-645112", None, {"payments_down": True}),
    "T-90603": ("double", "LK-645223", None, {}), "T-90604": ("return", "LK-645334", "LADDER-3", {"used": False}),
    "T-90605": ("damaged", "LK-645445", "TROWEL", {"photo": True}), "T-90606": ("late", "LK-645556", None, {}),
    "T-90607": ("return", "LK-645667", "BENCH-WD", {"used": False}),
    "T-90608": ("find:status", "bird feeder", "FEEDER", {"orders_down": True}),
    "T-90701": ("double", "LK-646001", None, {}),
    "T-90702": ("return", "LK-646112", "RUG-W", {"used": False}),
    "T-90703": ("damaged", "LK-646223", "POT-TC3", {"photo": True}),
    "T-90704": ("late", "LK-646334", None, {}),
    "T-90705": ("damaged", "LK-646445", "HOSE-25", {"photo": True}),
    "T-90706": ("person:H1", None, None, {}),
    "T-90707": ("status", "LK-646667", None, {}),
    "T-90708": ("wrong", "LK-646778", "CUSH-4", {"photo": True}),
}


def d(s):
    return date.fromisoformat(s) if s else None


def business_days_after(start: date, n: int) -> date:
    day = start
    while n:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in HOLIDAYS:
            n -= 1
    return day


def business_days_between(a: date, b: date) -> int:
    """Business days d with a < d <= b."""
    n, day = 0, a
    while day < b:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in HOLIDAYS:
            n += 1
    return n


def late_by(shipped: date) -> int:
    return business_days_between(business_days_after(shipped, 5), TODAY)


def act(tool, order_id, **kw):
    return {"tool": tool, "order_id": order_id, **kw}


def decide(db, task):
    intent, order_id, sku, info = READING[task["task_id"]]
    if intent.startswith("person:"):
        return "hand_to_person", []
    if intent == "outside":
        return "hand_to_person", []
    if intent.startswith("find:"):
        if info.get("orders_down"):
            return "ask_customer", []
        rows = db.execute("SELECT DISTINCT o.order_id FROM orders o JOIN order_items i USING(order_id) "
                          "WHERE o.customer_id = ? AND i.sku = ?", (task["customer_id"], sku)).fetchall()
        if len(rows) != 1:
            return "ask_customer", []
        intent, order_id = intent[5:], rows[0][0]
    o = db.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
    assert o["customer_id"] == task["customer_id"], task["task_id"]
    refunds = db.execute("SELECT * FROM refunds WHERE order_id = ?", (order_id,)).fetchall()
    if intent in ("status", "late", "lost"):
        if o["status"] == "processing":
            return "reply_only", []
        late = late_by(d(o["shipped_on"]))
        if late > 15:
            prefers = info.get("prefers")
            if prefers == "refund":
                return "resolve", [act("request_refund", order_id, amount=o["total"], reason_code="RFD-LATE",
                                       payment_id=None)]
            if prefers == "reship":
                items = db.execute("SELECT sku, quantity FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
                return "resolve", [act("reship_item", order_id, sku=i["sku"], quantity=i["quantity"]) for i in items]
            return "ask_customer", []
        if late > 5 and o["shipping_fee"] > 0 and not any(r["reason_code"] == "RFD-LATE" for r in refunds):
            return "resolve", [act("request_refund", order_id, amount=o["shipping_fee"], reason_code="RFD-LATE",
                                   payment_id=None)]
        return "reply_only", []
    if intent == "refund_eta":
        return "reply_only", []
    if intent == "missing_box":
        boxes = db.execute("SELECT * FROM shipments WHERE order_id = ? ORDER BY box", (order_id,)).fetchall()
        first = [b for b in boxes if b["delivered_on"]]
        missing = [b for b in boxes if not b["delivered_on"]]
        if business_days_between(d(first[0]["delivered_on"]), TODAY) < 2:
            return "reply_only", []
        if late_by(d(missing[0]["shipped_on"])) > 5:
            items = db.execute("SELECT sku, quantity FROM order_items WHERE order_id = ? AND box = ?",
                               (order_id, missing[0]["box"])).fetchall()
            return "resolve", [act("reship_item", order_id, sku=i["sku"], quantity=i["quantity"]) for i in items]
        return "reply_only", []
    if intent == "return":
        p = db.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        days = (TODAY - d(o["delivered_on"])).days
        if days <= 30 and not info["used"] and p["change_of_mind_return"]:
            return "resolve", [act("create_return_label", order_id, sku=sku, reason="change_of_mind")]
        return "reply_only", []
    if intent in ("damaged", "wrong"):
        days = (TODAY - d(o["delivered_on"])).days
        if days > 14:
            return "hand_to_person", []
        if not info["photo"]:
            return "ask_customer", []
        p = db.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        if intent == "wrong":
            return "resolve", [act("create_return_label", order_id, sku=sku, reason="wrong_item"),
                               act("reship_item", order_id, sku=sku, quantity=1)]
        acts = [act("reship_item", order_id, sku=sku, quantity=1)] if p["stock"] > 0 else \
            [act("request_refund", order_id, amount=p["unit_price"], reason_code="RFD-DAMAGE", payment_id=None)]
        if p["unit_price"] >= 50:
            acts.append(act("create_return_label", order_id, sku=sku, reason="damaged"))
        return "resolve", acts
    if intent == "double":
        if info.get("payments_down"):
            return "hand_to_person", []
        charges = db.execute("SELECT * FROM payments WHERE order_id = ? AND kind = 'charge' ORDER BY payment_id",
                             (order_id,)).fetchall()
        captured = [c for c in charges if c["status"] == "captured"]
        if len(captured) >= 2 and captured[-1]["amount"] == captured[0]["amount"]:
            return "resolve", [act("request_refund", order_id, amount=captured[-1]["amount"], reason_code="RFD-DOUBLE",
                                   payment_id=captured[-1]["payment_id"])]
        return "reply_only", []
    raise ValueError(intent)


def canon(actions):
    return sorted(json.dumps(a, sort_keys=True) for a in actions)


def main() -> None:
    data = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out"
    db = sqlite3.connect(data / "larkfield.sqlite")
    db.row_factory = sqlite3.Row
    tasks = [json.loads(line) for line in (data / "tasks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert set(READING) == {t["task_id"] for t in tasks}, set(READING) ^ {t["task_id"] for t in tasks}
    problems = 0
    for t in tasks:
        outcome, actions = decide(db, t)
        exp = t["expected"]
        if outcome != exp["outcome"] or canon(actions) != canon(exp["actions"]):
            problems += 1
            print(f"{t['task_id']}: rules say {outcome} {actions}; label says {exp['outcome']} {exp['actions']}")
    print(f"{len(tasks)} tasks checked, {problems} disagreements")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
