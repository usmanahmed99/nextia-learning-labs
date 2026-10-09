"""The one tool the model may ask for: a read-only order lookup.

The model only proposes a call. This code decides: it checks the argument, checks that the order
belongs to the ticket's customer, and only then reads the database. The customer ID never comes
from the model: the help-desk app knows who sent the ticket.
"""

import json
import re

from .orders import OrderBook

ORDER_ID = re.compile(r"^LK-\d{6}$")

GET_ORDER = {
    "type": "function",
    "function": {
        "name": "get_order",
        "description": ("Look up one of this customer's Larkfield orders by its order ID. Read-only. Returns the "
                        "status, the dates, the items and the total. Orders of other customers are not available."),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "The order ID, LK- and 6 digits."}},
            "required": ["order_id"],
            "additionalProperties": False,
        },
    },
}
TOOLS = [GET_ORDER]


class ToolRefused(Exception):
    """The application refused the model's proposal. `code` says why (for the log, not for the model)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def get_order(order_id: str, customer_id: str, book: OrderBook) -> dict:
    """Return the order if it exists and belongs to customer_id; otherwise raise ToolRefused."""
    if not isinstance(order_id, str) or not ORDER_ID.match(order_id):
        raise ToolRefused("invalid_argument", "The order ID must be LK- followed by 6 digits.")
    order = book.find(order_id)
    if order is None:
        raise ToolRefused("not_found", f"No order {order_id} is available for this customer.")
    if order["customer_id"] != customer_id:
        # Same message as "not found": the model (and so the customer) must not learn that the order exists.
        raise ToolRefused("other_customer", f"No order {order_id} is available for this customer.")
    del order["customer_id"]
    return order


def run_tool(name: str, arguments: str, customer_id: str, book: OrderBook) -> tuple[dict, str]:
    """Run one proposed call. Return (the result for the model, the outcome for the log)."""
    try:
        if name != "get_order":
            raise ToolRefused("unknown_tool", f"There is no tool named {name}.")
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            raise ToolRefused("invalid_argument", "The arguments are not valid JSON.") from None
        if not isinstance(args, dict) or set(args) != {"order_id"}:
            raise ToolRefused("invalid_argument", "get_order takes exactly one argument: order_id.")
        return {"ok": True, "order": get_order(args["order_id"], customer_id, book)}, "ok"
    except ToolRefused as refused:
        return {"ok": False, "error": str(refused)}, f"refused: {refused.code}"
