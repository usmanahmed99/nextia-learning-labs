"""Two gates between the model and the database: the schema, then the business rules."""

import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from .data import Ticket
from .providers import Completion
from .schema import TicketAnalysis
from .orders import OrderBook

SAFETY_WORDS = re.compile(r"(?i)\b(safety|unsafe|danger\w*|fire|smoke|burn(s|t|ed|ing)?|scorch\w*|spark\w*|shock|"
                          r"injur\w*|hurt|brûl\w*|incendie|étincel\w*|dangereu\w*)\b")  # "burner" is not a burn
LEGAL_WORDS = re.compile(r"(?i)\b(lawyer|court|sue|legal action|avocat|tribunal)\b")
FRENCH_WORDS = re.compile(r"(?i)\b(bonjour|merci|commande|je|ma|mon|pas|est|une?|vous|pouvez)\b")
# The assistant cannot refund, cancel or change anything, so a reply must not say "we have done it".
CLAIMS_DONE = re.compile(r"(?i)\b(i|we)(['’]ve| have) (refunded|issued|processed|approved|cancelled|changed)\b|"
                         r"(?<!confirm )(?<!whether )(?<!when )(?<!if )\b(your|a|the)( full)? refund( of [^ ]+)? has been "
                         r"(issued|processed|approved|sent)\b")
# Instructions to the assistant inside the ticket (rule H4): a person must look at the ticket.
INSTRUCTIONS = re.compile(r"(?i)\b(ignore|disregard|forget) (all |your |the |any )?(previous |prior )?"
                          r"(instructions|rules)\b")
# Asking for a password or a card number. "Don't send us your password" is fine: check what comes before.
ASKS_SECRET = re.compile(r"(?i)(?<!n't )(?<!n’t )(?<!not )(?<!never )\b(send|tell|give) us your (password|full card "
                         r"number|card number)\b")


@dataclass
class Problem:
    code: str
    message: str


@dataclass
class Verdict:
    analysis: TicketAnalysis | None
    problems: list[Problem] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.analysis is not None and not self.problems


def parse(completion: Completion) -> Verdict:
    """Gate 1: is there a complete answer, and does it follow the schema?"""
    if completion.refusal:
        return Verdict(None, [Problem("refusal", f"The model refused: {completion.refusal}")])
    if completion.finish_reason == "length":
        return Verdict(None, [Problem("truncated", "The answer was cut off at the token limit.")])
    if completion.finish_reason == "content_filter":
        return Verdict(None, [Problem("filtered", "The provider's content filter stopped the answer.")])
    if not completion.text:
        return Verdict(None, [Problem("empty", "The answer has no text.")])
    try:
        data = json.loads(completion.text)
    except json.JSONDecodeError as e:
        return Verdict(None, [Problem("malformed_json", f"Not valid JSON: {e.msg} at character {e.pos}.")])
    try:
        return Verdict(TicketAnalysis.model_validate(data))
    except ValidationError as e:
        details = "; ".join(f"{'.'.join(map(str, err['loc'])) or '(top)'}: {err['msg']}" for err in e.errors())
        return Verdict(None, [Problem("schema", details)])


def check_rules(analysis: TicketAnalysis, ticket: Ticket, book: OrderBook,
                looked_up: dict[str, dict] | None = None) -> list[Problem]:
    """Gate 2: valid JSON can still be wrong. Check what the policy and our data say."""
    problems = []
    looked_up = looked_up or {}
    if analysis.order:
        order_id = analysis.order.order_id
        order = book.find(order_id)
        if order_id not in ticket.text:
            problems.append(Problem("order_not_in_ticket", f"{order_id} does not appear in the ticket."))
        elif (order is None or order["customer_id"] != ticket.customer_id) and not analysis.needs_human:
            problems.append(Problem("order_not_customers",
                                    f"{order_id} is not one of this customer's orders, so a person must check it."))
        found = looked_up.get(order_id)
        if analysis.order.status is not None and (found is None or found["status"] != analysis.order.status):
            problems.append(Problem("status_not_from_lookup",
                                    f"The status {analysis.order.status!r} does not come from an order lookup."))
    if SAFETY_WORDS.search(ticket.text) and not analysis.needs_human:
        problems.append(Problem("safety_needs_human", "The ticket mentions safety, so needs_human must be true."))
    if LEGAL_WORDS.search(ticket.text) and not analysis.needs_human:
        problems.append(Problem("legal_needs_human", "The ticket mentions legal action, so needs_human must be true."))
    if INSTRUCTIONS.search(ticket.text) and not analysis.needs_human:
        problems.append(Problem("injection_needs_human", "The ticket gives instructions to the assistant (H4)."))
    if not ticket.text.strip() and not analysis.needs_human:
        problems.append(Problem("empty_needs_human", "The ticket has no text, so needs_human must be true."))
    french = len(FRENCH_WORDS.findall(ticket.text)) >= 3
    if ticket.text.strip() and analysis.language != ("fr" if french else "en"):
        problems.append(Problem("wrong_language", f"The ticket looks {'French' if french else 'English'}."))
    if CLAIMS_DONE.search(analysis.reply):
        problems.append(Problem("claims_action", "The reply says that a refund or a change was made."))
    if ASKS_SECRET.search(analysis.reply):
        problems.append(Problem("asks_secret", "The reply asks for a password or a card number."))
    return problems


def validate(completion: Completion, ticket: Ticket, book: OrderBook,
             looked_up: dict[str, dict] | None = None) -> Verdict:
    verdict = parse(completion)
    if verdict.analysis is not None:
        verdict.problems = check_rules(verdict.analysis, ticket, book, looked_up)
    return verdict
