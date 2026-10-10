"""The explicit result of running one case with one design: what the assistant read, proposed,
wrote and said, and why it stopped. Typed, so a test or the evaluator can check it."""

from typing import Literal

from pydantic import BaseModel, Field


class ToolEvent(BaseModel):
    step: int
    tool: str
    arguments: dict = Field(default_factory=dict)
    allowed: bool                       # did a control let it run?
    blocked_reason: str = ""
    ok: bool = False                    # did the service succeed (when allowed)?
    code: str = "ok"
    summary: str = ""                   # a short, non-sensitive description for the trace
    read_order_tenant: str = ""         # for a read of an order: the order's tenant (to catch cross-tenant)
    read_path: str = ""                 # for read_file
    fetch_host: str = ""                # for fetch_url
    docs: list[str] = Field(default_factory=list)   # for search_docs: "passage tenant access" of each passage read


class Proposal(BaseModel):
    tool: str                           # issue_refund, create_return_label, send_email
    arguments: dict
    approval_id: str = ""               # the waiting approval in the database (when a person must approve)
    approved: bool = False
    approver: str = ""
    approver_role: str = ""
    executed: bool = False
    execution_id: str = ""
    refused_reason: str = ""            # why a control refused to execute it (even if a person said yes)


class RunState(BaseModel):
    run_id: str = ""                    # a new ID for every run; every audit event of the run carries it
    case_id: str
    design: str
    model: str
    tenant: str
    user: str
    role: str = ""
    kind: str = "task"
    step: int = 0
    answer: str = ""                    # the reply draft the assistant produced
    tool_events: list[ToolEvent] = Field(default_factory=list)
    proposals: list[Proposal] = Field(default_factory=list)
    stop_reason: str = ""               # finished, max_steps, provider_error, content_filter, auth_error, filter_block,
                                        # no_recording, revoked
    filter_verdict: str = ""            # if the input filter ran: allow / block + why
    usage_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = 0.0
    model_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
    replay_notes: int = 0               # model decisions the mock replayed from a different recorded request

    def note(self, msg: str) -> None:
        self.errors.append(msg)
