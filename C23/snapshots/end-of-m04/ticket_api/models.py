from datetime import datetime
from typing import Literal
from uuid import UUID

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
                    "score": 0.9,
                    "model_version": "keywords-1.0",
                }
            ]
        }
    )

    category: Category = Field(description="The team that should handle the ticket.")
    priority: int = Field(ge=1, le=3, description="1 is the most urgent, 3 the least.")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Deprecated: use score. The same value. Removed in version 2.0.",
        json_schema_extra={"deprecated": True},
    )
    score: float = Field(ge=0, le=1, description="How sure the classifier is, from 0 to 1.")
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
    score: float = Field(ge=0, le=1)
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


# ---------- tickets (Module 3 of the databases course) ----------

Team = Literal["billing", "login", "shipping", "account", "other"]
Status = Literal["open", "pending", "resolved", "closed"]


class TicketSummary(BaseModel):
    """One row of the ticket list."""

    ticket_id: str = Field(examples=["T-30002"])
    customer_id: str
    customer_name: str
    subject: str
    team: Team
    priority: int = Field(ge=1, le=3)
    status: Status
    created_at: datetime
    message_count: int = Field(description="Messages after the first one.")
    last_message_at: datetime | None
    last_run_model: str | None = Field(description="The model of the ticket's latest AI run.")
    last_run_status: str | None


class TicketPage(BaseModel):
    items: list[TicketSummary] = Field(description="The newest ticket first.")
    next: str | None = Field(
        description="Give this value as `after` to get the next page. Empty on the last page."
    )


class Message(BaseModel):
    message_id: int
    author: Literal["customer", "agent"]
    body: str
    created_at: datetime


class MessageIn(BaseModel):
    """A new message on a ticket."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"author": "agent", "body": "We have sent a new parcel today."}]
        },
    )

    author: Literal["customer", "agent"]
    body: str = Field(min_length=1, max_length=5000)


class AttachmentInfo(BaseModel):
    attachment_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    status: Literal["pending", "stored", "rejected"]
    uploaded_at: datetime | None


class TicketDetail(BaseModel):
    ticket_id: str
    customer_id: str
    customer_name: str
    subject: str
    body: str
    channel: str
    team: Team
    priority: int
    status: Status
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    message_count: int
    messages: list[Message]
    attachments: list[AttachmentInfo]


# ---------- attachments (Module 5) ----------

ContentType = Literal["image/png", "image/jpeg", "application/pdf", "text/plain"]


class AttachmentIn(BaseModel):
    """The file that a client wants to upload."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"file_name": "photo-1.png", "content_type": "image/png", "size_bytes": 48213}
            ]
        },
    )

    file_name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9._-]+$")
    content_type: ContentType
    size_bytes: int = Field(
        gt=0, description="The size of the file. The API checks it after the upload."
    )


class UploadLink(BaseModel):
    attachment_id: str
    upload_url: str = Field(description="PUT the file to this URL before it expires.")
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str] = Field(description="Send these headers with the file.")
    expires_at: datetime
    max_bytes: int


class DownloadLink(BaseModel):
    url: str = Field(description="GET the file from this URL before it expires.")
    expires_at: datetime


# ---------- similar tickets (Module 5) ----------


class SimilarTicket(BaseModel):
    ticket_id: str
    subject: str
    team: Team
    status: Status
    created_at: datetime
    distance: float = Field(description="Cosine distance: 0 is the same direction, 2 the opposite.")


class SimilarList(BaseModel):
    embedding_version: str
    items: list[SimilarTicket] = Field(description="The closest ticket first.")


# ---------- who is calling (the authentication course, Module 2) ----------

Role = Literal["owner", "staff", "read_only"]


class MembershipInfo(BaseModel):
    tenant_id: str = Field(examples=["larkfield"])
    tenant_name: str
    role: Role


class Me(BaseModel):
    """The caller, as the API sees them: from the checked token, and from the API's own tables."""

    user_id: str = Field(description="The identity provider's stable user ID (the token's sub).")
    kind: Literal["user", "service"]
    name: str | None = Field(description="From the API's user table; None if it does not know.")
    platform_role: str | None
    client_id: str = Field(description="The application that got the token.")
    scopes: list[str] = Field(description="What the application may do for the caller.")
    token_expires_at: datetime
    memberships: list[MembershipInfo] = Field(
        description="The organizations of the caller, with the role in each. Not from the token."
    )


# ---------- help documents (the authentication course, Module 4) ----------


class DocumentHit(BaseModel):
    """One matching document, with what a citation needs."""

    doc_id: str
    version: int
    title: str
    access: Literal["public", "staff"]
    snippet: str = Field(description="The matching words, between <b> and </b>.")


class DocumentResults(BaseModel):
    access_level: Literal["public", "staff"] = Field(
        description="What the caller's role may see: staff includes the staff-only documents."
    )
    results: list[DocumentHit]
