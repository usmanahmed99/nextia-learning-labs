"""The shape of the assistant's answer (from the LLM applications course, unchanged).

The harness checks every saved output against it again: a recording made with structured output
can still be cut off or empty.
"""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Team = Literal["delivery", "returns", "payment", "warranty", "account"]
OrderStatus = Literal["processing", "shipped", "delivered", "return_requested", "return_received", "refunded",
                      "cancelled"]


class OrderRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(pattern=r"^LK-\d{6}$", description="The order ID exactly as the ticket writes it.")
    status: OrderStatus | None = Field(description="Only from an order lookup result; otherwise null.")


class TicketAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Literal["en", "fr"]
    team: Team
    needs_human: bool
    reason: str = Field(max_length=300)
    confidence: Literal["low", "medium", "high"]
    order: OrderRef | None
    reply: str = Field(min_length=1, max_length=1200)


def parse_answer(text: str | None) -> tuple[dict | None, str]:
    """(the validated answer as a dict, "") or (None, the problem)."""
    if not text:
        return None, "empty"
    try:
        return TicketAnalysis.model_validate(json.loads(text)).model_dump(), ""
    except json.JSONDecodeError as e:
        return None, f"malformed_json: {e.msg}"
    except ValidationError as e:
        return None, "schema: " + "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors())
