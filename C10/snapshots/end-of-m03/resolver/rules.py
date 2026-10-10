"""Grace's resolution rules (W1-W8 of prompts/policy.md) written as code.

The fixed workflow and the router use these rules: once the kind of request and the order are known,
code decides the action. A model never decides an amount or a date here.
Input: the kind of request, the order as get_order returns it, and the payments for a double charge.
"""

from dataclasses import dataclass, field

DAMAGE_LABEL_FROM = 50.00


@dataclass
class Decision:
    outcome: str
    rule: str
    actions: list[dict] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


def _item(order: dict, sku: str | None, product_words: str = "") -> dict | None:
    items = order["items"]
    if sku:
        for i in items:
            if i["sku"] == sku:
                return i
    words = product_words.lower()
    matches = [i for i in items if any(w in words for w in i["product"].lower().replace("(", " ").split() if len(w) > 3)]
    if len(matches) == 1:
        return matches[0]
    return items[0] if len(items) == 1 else None


def decide(kind: str, order: dict, *, payments: dict | None = None, sku: str | None = None, text: str = "",
           photo: bool = False, used: bool = False, prefers: str = "") -> Decision:
    """kind: status, late, lost, missing_box, return, damaged, wrong_item, double_charge, refund_eta."""
    oid = order["order_id"]
    if kind == "refund_eta":
        return Decision("reply_only", "W8", facts=[f"{oid}: refunds {order['refunds']}"])
    if kind in ("status", "late", "lost", "missing_box"):
        boxes = order.get("boxes") or []
        missing = [b for b in boxes if b.get("shipped_on") and not b.get("delivered_on")]
        arrived = [b for b in boxes if b.get("delivered_on")]
        if order["status"] == "processing":
            return Decision("reply_only", "W1", facts=[f"{oid} is processing"])
        if arrived and missing:   # W4: an order in several boxes, one missing
            box = missing[0]
            if arrived[0]["business_days_since_delivery"] < 2:
                return Decision("reply_only", "W4", facts=[f"box {arrived[0]['box']} arrived "
                                                           f"{arrived[0]['business_days_since_delivery']} business day(s) ago"])
            if box["business_days_late"] > 5:
                acts = [{"tool": "reship_item", "order_id": oid, "sku": i["sku"], "quantity": i["quantity"]}
                        for i in order["items"] if i["box"] == box["box"]]
                return Decision("resolve", "W4", acts, [f"box {box['box']} is {box['business_days_late']} business days late"])
            return Decision("reply_only", "W4", facts=[f"box {box['box']} is {box['business_days_late']} business days late"])
        late = order.get("business_days_late")
        if late is None:
            return Decision("reply_only", "W1", facts=[f"{oid} is {order['status']}"])
        if late > 15:
            if prefers == "refund":
                return Decision("resolve", "W3", [{"tool": "request_refund", "order_id": oid, "amount": order["total"],
                                                   "reason_code": "RFD-LATE", "payment_id": None}],
                                [f"{oid} is {late} business days late: lost"])
            if prefers == "replacement":
                return Decision("resolve", "W3", [{"tool": "reship_item", "order_id": oid, "sku": i["sku"],
                                                   "quantity": i["quantity"]} for i in order["items"]],
                                [f"{oid} is {late} business days late: lost"])
            return Decision("ask_customer", "W3", facts=[f"{oid} is {late} business days late: lost; ask replacement or refund"])
        if late > 5:
            already = any(r["reason_code"] == "RFD-LATE" for r in order["refunds"])
            if order["shipping_fee"] > 0 and not already:
                return Decision("resolve", "W2", [{"tool": "request_refund", "order_id": oid,
                                                   "amount": order["shipping_fee"], "reason_code": "RFD-LATE",
                                                   "payment_id": None}], [f"{oid} is {late} business days late"])
            return Decision("reply_only", "W2", facts=[f"{oid} is {late} business days late; fee "
                                                       f"{order['shipping_fee']:.2f}, already refunded: {already}"])
        return Decision("reply_only", "W1", facts=[f"{oid} is {late} business days late (expected {order.get('expected_by')})"])
    if kind == "return":
        item = _item(order, sku, text)
        days = order.get("days_since_delivery")
        if item is None or days is None:
            return Decision("hand_to_person", "W6", facts=[f"{oid}: cannot tell which item, or not delivered"])
        if days <= 30 and not used and item["change_of_mind_return"]:
            return Decision("resolve", "W6", [{"tool": "create_return_label", "order_id": oid, "sku": item["sku"],
                                               "reason": "change_of_mind"}], [f"delivered {days} days ago"])
        return Decision("reply_only", "W6", facts=[f"delivered {days} days ago; used: {used}; "
                                                   f"returnable: {item['change_of_mind_return']}"])
    if kind in ("damaged", "wrong_item"):
        item = _item(order, sku, text)
        days = order.get("days_since_delivery")
        if item is None or days is None:
            return Decision("hand_to_person", "W5", facts=[f"{oid}: cannot tell which item, or not delivered"])
        if days > 14:
            return Decision("hand_to_person", "W5", facts=[f"delivered {days} days ago: a warranty claim"])
        if not photo:
            return Decision("ask_customer", "W5", facts=["no photo"])
        if kind == "wrong_item":
            return Decision("resolve", "W5", [
                {"tool": "create_return_label", "order_id": oid, "sku": item["sku"], "reason": "wrong_item"},
                {"tool": "reship_item", "order_id": oid, "sku": item["sku"], "quantity": 1}], ["wrong item"])
        acts = [{"tool": "reship_item", "order_id": oid, "sku": item["sku"], "quantity": 1}] if item["in_stock"] else \
            [{"tool": "request_refund", "order_id": oid, "amount": item["unit_price"], "reason_code": "RFD-DAMAGE",
              "payment_id": None}]
        if item["unit_price"] >= DAMAGE_LABEL_FROM:
            acts.append({"tool": "create_return_label", "order_id": oid, "sku": item["sku"], "reason": "damaged"})
        return Decision("resolve", "W5", acts, [f"delivered {days} days ago; in stock: {item['in_stock']}"])
    if kind == "double_charge":
        if payments is None:
            return Decision("hand_to_person", "W7", facts=["the payments could not be read"])
        captured = [p for p in payments["payments"] if p["kind"] == "charge" and p["status"] == "captured"]
        if len(captured) >= 2 and captured[0]["amount"] == captured[-1]["amount"]:
            extra = captured[-1]
            return Decision("resolve", "W7", [{"tool": "request_refund", "order_id": oid, "amount": extra["amount"],
                                               "reason_code": "RFD-DOUBLE", "payment_id": extra["payment_id"]}],
                            [f"two captured charges of {extra['amount']:.2f}"])
        return Decision("reply_only", "W7", facts=[f"captured charges: {len(captured)}"])
    return Decision("hand_to_person", "outside", facts=[f"kind {kind}"])
