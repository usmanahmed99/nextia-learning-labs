"""One ticket in, one checked result out."""

from dataclasses import asdict, dataclass, field

from .context import build_request
from .data import Ticket
from .loop import Limits, LoopResult, Step, run_tool_loop
from .orders import OrderBook
from .providers import Completion, ProviderError
from .retry import RetryPolicy, call_with_retry
from .schema import TicketAnalysis, response_format
from .tools import TOOLS
from .usage import UsageLog
from .validate import Problem, validate


@dataclass
class Outcome:
    ticket_id: str
    status: str                      # "valid", "rejected" (a gate stopped it) or "failed" (no answer)
    analysis: TicketAnalysis | None
    problems: list[Problem] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    completions: list[Completion] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "status": self.status,
            "analysis": self.analysis.model_dump() if self.analysis else None,
            "problems": [asdict(p) for p in self.problems],
            "tool_steps": [asdict(s) for s in self.steps],
            "error": self.error,
        }


def analyse_ticket(ticket: Ticket, provider, model: str, prompt: str = "v2", structured: bool = True,
                   tools: bool = True, book: OrderBook | None = None, limits: Limits = Limits(),
                   retry: RetryPolicy = RetryPolicy(), log: UsageLog | None = None,
                   reasoning_effort: str = "") -> Outcome:
    book = book or OrderBook()
    request = build_request(ticket, model, prompt, response_format() if structured else None,
                            TOOLS if tools else None, reasoning_effort)

    def complete(req: dict) -> Completion:
        completion = call_with_retry(lambda: provider.complete(req), retry)
        if log:
            log.record(completion, model, ticket.ticket_id, prompt)
        return completion

    try:
        if tools:
            result = run_tool_loop(complete, request, ticket.customer_id, book, limits)
        else:
            completion = complete(request)
            result = LoopResult(completion, [completion])
    except ProviderError as error:
        return Outcome(ticket.ticket_id, "failed", None, error=str(error))
    if result.stopped:
        return Outcome(ticket.ticket_id, "failed", None, steps=result.steps, completions=result.completions,
                       error=f"The tool loop was stopped: {result.stopped}.")
    verdict = validate(result.completion, ticket, book, result.looked_up)
    return Outcome(ticket.ticket_id, "valid" if verdict.valid else "rejected", verdict.analysis, verdict.problems,
                   result.steps, result.completions)
