"""What a decision looks like: the proposed resolution and its write actions, as validated data.

The model writes a resolution (as the arguments of the `finish` tool, or as structured output).
Pydantic checks it here; a resolution that does not fit is refused and the model is told why.
The JSON schemas below are what the model sees; the Pydantic models are what the code trusts.
"""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ORDER_ID = r"^LK-\d{6}$"
Outcome = Literal["resolve", "reply_only", "ask_customer", "hand_to_person"]
WRITE_TOOLS = ("create_return_label", "reship_item", "request_refund")


class ReturnLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["create_return_label"]
    order_id: str = Field(pattern=ORDER_ID)
    sku: str = Field(min_length=2, max_length=20)
    reason: Literal["change_of_mind", "damaged", "wrong_item"]


class Reship(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["reship_item"]
    order_id: str = Field(pattern=ORDER_ID)
    sku: str = Field(min_length=2, max_length=20)
    quantity: int = Field(ge=1, le=10)


class Refund(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["request_refund"]
    order_id: str = Field(pattern=ORDER_ID)
    amount: float = Field(gt=0, le=5000)
    reason_code: Literal["RFD-LATE", "RFD-DAMAGE", "RFD-DOUBLE"]
    payment_id: str | None = None

    @field_validator("amount")
    @classmethod
    def cents(cls, v: float) -> float:
        return round(v, 2)


Action = Annotated[Union[ReturnLabel, Reship, Refund], Field(discriminator="tool")]


class Resolution(BaseModel):
    """The decision for one ticket. Only `resolve` may carry actions; every action waits for approval."""
    model_config = ConfigDict(extra="forbid")
    outcome: Outcome
    rule: str = Field(max_length=40)
    actions: list[Action] = Field(default_factory=list, max_length=4)
    reply: str = Field(max_length=2000)
    reason: str = Field(max_length=600)

    @field_validator("actions")
    @classmethod
    def only_when_resolving(cls, v, info):
        if v and info.data.get("outcome") != "resolve":
            raise ValueError("only the outcome 'resolve' may propose actions")
        if not v and info.data.get("outcome") == "resolve":
            raise ValueError("the outcome 'resolve' needs at least one action")
        return v


def action_from_flat(flat: dict) -> dict:
    """The model's flat action (every field present, unused ones null) -> the fields of one write tool."""
    tool = flat.get("tool")
    keep = {"create_return_label": ("order_id", "sku", "reason"), "reship_item": ("order_id", "sku", "quantity"),
            "request_refund": ("order_id", "amount", "reason", "payment_id")}.get(tool, tuple(flat))
    out = {"tool": tool}
    for name in keep:
        if name == "reason" and tool == "request_refund":
            out["reason_code"] = flat.get("reason")
        elif name in flat:
            out[name] = flat[name]
    return out


def parse_resolution(data: dict) -> Resolution:
    """Validate a resolution written by a model. Raises ValidationError with readable messages."""
    data = dict(data)
    data["actions"] = [action_from_flat(a) if isinstance(a, dict) else a for a in data.get("actions") or []]
    return Resolution.model_validate(data)


def errors_text(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()[:5])


# ---- the JSON schemas that the model sees (strict mode: every property required, unused ones null)
FLAT_ACTION = {
    "type": "object",
    "properties": {
        "tool": {"type": "string", "enum": list(WRITE_TOOLS)},
        "order_id": {"type": "string", "description": "LK- and 6 digits"},
        "sku": {"type": ["string", "null"], "description": "the item's SKU, for a label or a reshipment"},
        "quantity": {"type": ["integer", "null"], "description": "for reship_item"},
        "amount": {"type": ["number", "null"], "description": "for request_refund, in dollars"},
        "reason": {"type": ["string", "null"],
                   "description": "label: change_of_mind, damaged or wrong_item; refund: RFD-LATE, RFD-DAMAGE or "
                                  "RFD-DOUBLE"},
        "payment_id": {"type": ["string", "null"], "description": "for a double charge: the extra charge"},
    },
    "required": ["tool", "order_id", "sku", "quantity", "amount", "reason", "payment_id"],
    "additionalProperties": False,
}

RESOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "outcome": {"type": "string", "enum": ["resolve", "reply_only", "ask_customer", "hand_to_person"]},
        "rule": {"type": "string", "description": "the policy rule that decides it, for example W5 or H1"},
        "actions": {"type": "array", "items": FLAT_ACTION,
                    "description": "the changes to propose for approval; empty unless the outcome is resolve"},
        "reply": {"type": "string", "description": "the reply draft for the customer, in their language"},
        "reason": {"type": "string", "description": "one or two sentences for the approver: why"},
    },
    "required": ["outcome", "rule", "actions", "reply", "reason"],
    "additionalProperties": False,
}
