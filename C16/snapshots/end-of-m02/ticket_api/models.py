from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["billing", "login", "shipping", "account", "other"]


class TicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=5000)


class Classification(BaseModel):
    category: Category
    priority: int = Field(ge=1, le=3)
    confidence: float = Field(ge=0, le=1)
    model_version: str
