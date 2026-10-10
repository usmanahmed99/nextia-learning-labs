"""The explicit state of one task: typed fields, not a chat history.

The conversation with the model is only the working context of one step. What the task knows
(goal, evidence), where it is (status, step), what was decided (proposal), who approved it, what was
written (operations) and what went wrong (errors) live here. The checkpoint store saves this object
after every step, so that a task can stop and resume, and a trace can be read later.
"""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .schema import Resolution

Status = Literal["running", "waiting_approval", "executing", "done", "handed_to_person", "stopped", "failed"]


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Evidence(BaseModel):
    """One tool result that the application really received (the model cannot add evidence)."""
    step: int
    tool: str
    arguments: dict
    ok: bool
    code: str
    data: object = None
    error: str = ""
    order_ids: list[str] = Field(default_factory=list)


class Event(BaseModel):
    """One thing that happened, for the trace: a model call, a tool call, an approval, a write, an error."""
    at: str = Field(default_factory=now)
    step: int
    kind: Literal["model", "tool", "proposal", "approval", "write", "reconcile", "stop", "error", "note", "plan"]
    name: str = ""
    detail: dict = Field(default_factory=dict)


class Approval(BaseModel):
    decision: Literal["approved", "rejected"]
    approver: str
    role: Literal["agent", "team_lead", "grace"]
    note: str = ""
    at: str = Field(default_factory=now)
    proposal_digest: str          # what was approved: a change to the proposal needs a new approval


class Operation(BaseModel):
    """One approved write. Saved BEFORE the call (write-ahead), so a crash leaves a trace of the attempt."""
    op_id: str
    tool: str
    arguments: dict
    status: Literal["pending", "done", "failed", "uncertain"] = "pending"
    attempts: int = 0
    result: dict | None = None
    error: str = ""


class Usage(BaseModel):
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0      # None when a model's price is unknown
    model_seconds: float = 0.0        # the time spent waiting for the model (recorded latency in replays)


class TaskState(BaseModel):
    run_id: str
    task_id: str
    customer_id: str
    variant: str
    model: str
    goal: str                                   # the ticket text: what the customer wants
    attachments: list[str] = Field(default_factory=list)
    status: Status = "running"
    step: int = 0                               # model calls made so far
    plan: list[str] = Field(default_factory=list)   # the current plan only; earlier plans are in the events
    evidence: list[Evidence] = Field(default_factory=list)
    proposal: Resolution | None = None
    approval: Approval | None = None
    operations: list[Operation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    stop_reason: str = ""
    usage: Usage = Field(default_factory=Usage)
    events: list[Event] = Field(default_factory=list)
    messages: list[dict] = Field(default_factory=list)   # the working context of the model (to resume a loop)
    faults_seen: list[list[str]] = Field(default_factory=list)   # simulated failures already used (tool, mode)
    started_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)

    def log(self, kind: str, name: str = "", **detail) -> None:
        self.events.append(Event(step=self.step, kind=kind, name=name, detail=detail))

    def evidence_digest(self) -> str:
        """A short fingerprint of the evidence so far (the mock uses it to say when a state differs)."""
        text = json.dumps([[e.tool, e.arguments, e.ok, e.code] for e in self.evidence], sort_keys=True)
        return hashlib.sha256(text.encode()).hexdigest()[:8]

    def seen_orders(self) -> set[str]:
        return {o for e in self.evidence if e.ok for o in e.order_ids}


def proposal_digest(resolution: Resolution) -> str:
    text = json.dumps([a.model_dump() for a in resolution.actions], sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:12]
