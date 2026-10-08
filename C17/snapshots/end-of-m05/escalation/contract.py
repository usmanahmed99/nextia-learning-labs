"""The inference contract: what a ticket must look like before the model scores it.

The model learned from 11 features. This file says, for each one, its name,
its type, the values it may take, and whether it may be missing. The API and
the batch job both check tickets with these classes, so the two paths always
apply the same rules.
"""

import math

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

# The order of the columns that the pipeline was fitted on (C05 ticket_model.py).
FEATURES = [
    "channel",
    "team",
    "segment",
    "region",
    "priority",
    "order_value",
    "word_count",
    "customer_tenure_days",
    "prior_tickets_90d",
    "created_hour",
    "prior_escalations_90d",
]
CATEGORIES = ["channel", "team", "segment", "region"]


class TicketFeatures(BaseModel):
    """The 11 features of one ticket, as they are when the ticket is created."""

    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=30, description="How the customer contacted us.")
    team: str = Field(min_length=1, max_length=30, description="The team that owns the ticket.")
    segment: str = Field(min_length=1, max_length=30, description="The kind of customer.")
    region: str = Field(min_length=1, max_length=30, description="The customer's region.")
    priority: int = Field(ge=1, le=3, description="1 is the most urgent, 3 the least.")
    order_value: float | None = Field(
        ge=0, le=5000, description="The order's value in dollars. Null if there is no order."
    )
    word_count: int = Field(ge=0, le=10000, description="Words in the first message.")
    customer_tenure_days: int | None = Field(
        ge=0, le=20000, description="Days since the customer's first order. Null for a guest."
    )
    prior_tickets_90d: int = Field(ge=0, le=500, description="The customer's tickets in the last 90 days.")
    created_hour: int = Field(ge=0, le=23, description="The hour the ticket was created (0 to 23).")
    prior_escalations_90d: int = Field(ge=0, le=500, description="The customer's escalations in the last 90 days.")


class TicketIn(TicketFeatures):
    """A ticket to score: its ID and its features."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "ticket_id": "T-120001",
                    "channel": "email",
                    "team": "payment",
                    "segment": "home",
                    "region": "west",
                    "priority": 1,
                    "order_value": 89.5,
                    "word_count": 112,
                    "customer_tenure_days": 400,
                    "prior_tickets_90d": 2,
                    "created_hour": 10,
                    "prior_escalations_90d": 1,
                }
            ]
        },
    )

    ticket_id: str = Field(pattern=r"^T-\d{6}$", description="The ticket's ID, for example T-120001.")


def unknown_categories(ticket: TicketFeatures, known: dict[str, list[str]]) -> list[str]:
    """Warnings for category values that the model never saw in training.

    They are allowed: the one-hot encoder gives them no column, so the model
    scores them as "none of the known values". Many of them mean the input
    has changed, so the service reports and counts them.
    """
    warnings = []
    for name in CATEGORIES:
        value = getattr(ticket, name)
        if value not in known[name]:
            warnings.append(f"{name}: {value!r} is a value the model never saw")
    return warnings


def to_frame(tickets: list[TicketFeatures]) -> pd.DataFrame:
    """The tickets as a table with the training columns, in the training order.

    A missing number (None) becomes NaN, so the pipeline's imputer fills it
    with the training median, exactly as in training. Do not fill it here.
    """
    rows = [t.model_dump(include=set(FEATURES)) for t in tickets]
    frame = pd.DataFrame(rows, columns=FEATURES)
    for name in FEATURES:
        if name not in CATEGORIES:
            frame[name] = frame[name].astype("float64")
    return frame


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))
