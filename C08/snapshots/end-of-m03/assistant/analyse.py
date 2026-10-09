"""One ticket in, one checked result out."""

from dataclasses import asdict, dataclass, field

from .context import build_request
from .data import Ticket
from .orders import OrderBook
from .providers import Completion, ProviderError
from .schema import TicketAnalysis, response_format
from .validate import Problem, validate


@dataclass
class Outcome:
    ticket_id: str
    status: str                      # "valid", "rejected" (a gate stopped it) or "failed" (no answer)
    analysis: TicketAnalysis | None
    problems: list[Problem] = field(default_factory=list)
    completions: list[Completion] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "status": self.status,
            "analysis": self.analysis.model_dump() if self.analysis else None,
            "problems": [asdict(p) for p in self.problems],
            "error": self.error,
        }


def analyse_ticket(ticket: Ticket, provider, model: str, prompt: str = "v2", structured: bool = True,
                   book: OrderBook | None = None) -> Outcome:
    book = book or OrderBook()
    request = build_request(ticket, model, prompt, response_format() if structured else None)
    try:
        completion = provider.complete(request)
    except ProviderError as error:
        return Outcome(ticket.ticket_id, "failed", None, error=str(error))
    verdict = validate(completion, ticket, book)
    return Outcome(ticket.ticket_id, "valid" if verdict.valid else "rejected", verdict.analysis, verdict.problems,
                   [completion])
