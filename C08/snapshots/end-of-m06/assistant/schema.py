"""The shape of the assistant's answer, as a Pydantic model and as the JSON schema sent to the provider."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


def response_format() -> dict:
    """Ask the provider for JSON that follows the schema (structured output, strict mode)."""
    return {
        "type": "json_schema",
        "json_schema": {"name": "ticket_analysis", "strict": True, "schema": TicketAnalysis.model_json_schema()},
    }
