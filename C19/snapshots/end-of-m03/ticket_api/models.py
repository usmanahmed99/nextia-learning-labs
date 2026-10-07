from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["billing", "login", "shipping", "account", "other"]


class TicketIn(BaseModel):
    """A support ticket to classify."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "subject": "Charged twice for March",
                    "body": "My card was charged two times for the same invoice.",
                }
            ]
        },
    )

    subject: str = Field(
        min_length=1, max_length=120, description="The short title of the ticket."
    )
    body: str = Field(
        default="", max_length=5000, description="The customer's message. Optional."
    )


class Classification(BaseModel):
    """The predicted category and priority of a ticket."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "category": "billing",
                    "priority": 1,
                    "confidence": 0.9,
                    "model_version": "keywords-1.0",
                }
            ]
        }
    )

    category: Category = Field(description="The team that should handle the ticket.")
    priority: int = Field(ge=1, le=3, description="1 is the most urgent, 3 the least.")
    confidence: float = Field(
        ge=0, le=1, description="How sure the classifier is, from 0 to 1."
    )
    model_version: str = Field(description="The classifier that made the prediction.")


class CategoryList(BaseModel):
    categories: list[Category] = Field(
        description="Every category that /v1/classify can return."
    )


class HistoryItem(BaseModel):
    """One classification that the API made. It has no ticket text."""

    request_id: str = Field(description="The request that made the classification.")
    category: Category
    priority: int = Field(ge=1, le=3)
    confidence: float = Field(ge=0, le=1)
    model_version: str
    created_at: datetime = Field(description="When the API made it (UTC).")


class HistoryList(BaseModel):
    items: list[HistoryItem] = Field(description="The newest classification first.")


class Health(BaseModel):
    status: Literal["ok"]


class Readiness(BaseModel):
    status: Literal["ready"]


class ErrorDetail(BaseModel):
    code: str = Field(description="A stable code that a program can check.")
    message: str = Field(description="A short explanation for a person.")
    request_id: str | None = Field(
        default=None, description="Give this ID when you report a problem."
    )
    fields: list[str] = Field(
        default=[], description="The request fields that are not valid, if any."
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "code": "invalid_request",
                        "message": "The request is not valid.",
                        "fields": ["subject"],
                    }
                }
            ]
        }
    )

    error: ErrorDetail
