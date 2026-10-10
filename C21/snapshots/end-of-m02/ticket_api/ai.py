"""The AI work for one ticket: what the API asks the AI provider, and how it reads the answers.

Three tasks for every new ticket (the scaling course, Module 1):
- classify:    which team gets the ticket, and how urgent it is (a chat model, JSON answer)
- draft_reply: a first reply that a person checks before it is sent (a chat model, text)
- embed:       a vector of the ticket's text, for finding similar tickets (an embedding model)

The requests use the OpenAI-compatible API, so the same code talks to the simulated
provider on your computer and to a real provider.
"""

import json
from dataclasses import dataclass

CHAT_MODEL = "chat-small"
EMBED_MODEL = "embed-small"
EMBED_DIMENSIONS = 384
CLASSIFY_PROMPT = "classify-v1"
DRAFT_PROMPT = "draft-v3"
EMBEDDING_VERSION = "embed-small-384-v1"
TEAMS = ("billing", "login", "shipping", "account", "other")

CLASSIFY_SYSTEM = (
    "You sort the support tickets of Larkfield, an online shop for garden and home products. "
    "Choose the team that handles the ticket: billing (payments, invoices, refunds), login "
    "(passwords, sign-in, two-factor), shipping (parcels, delivery, tracking), account (account "
    "details, users, company data) or other. Choose the priority: 1 = the customer cannot use "
    "the service or lost money, 2 = normal, 3 = a question or a suggestion. Answer only with JSON."
)

DRAFT_SYSTEM = (
    "You write the first reply to a support ticket of Larkfield, an online shop for garden and "
    "home products. A person on the help desk reads your reply before it is sent. Write 2 to 4 "
    "short sentences in plain English. Thank the customer, say what happens next, and ask for "
    "one missing detail if one is needed. Do not promise a refund or a date. No greeting line "
    "with a name, no signature."
)

CLASSIFY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "team": {"type": "string", "enum": list(TEAMS)},
                "priority": {"type": "integer", "enum": [1, 2, 3]},
            },
            "required": ["team", "priority"],
            "additionalProperties": False,
        },
    },
}


def ticket_text(subject: str, body: str) -> str:
    return f"Subject: {subject}\n\n{body}".strip()


def classify_request(subject: str, body: str) -> dict:
    return {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": ticket_text(subject, body)},
        ],
        "response_format": CLASSIFY_SCHEMA,
        "max_completion_tokens": 50,
        "reasoning_effort": "none",
    }


def draft_request(subject: str, body: str) -> dict:
    return {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": DRAFT_SYSTEM},
            {"role": "user", "content": ticket_text(subject, body)},
        ],
        "max_completion_tokens": 200,
        "reasoning_effort": "none",
    }


def embed_request(subject: str, body: str) -> dict:
    return {
        "model": EMBED_MODEL,
        "input": ticket_text(subject, body),
        "dimensions": EMBED_DIMENSIONS,
    }


@dataclass(frozen=True)
class Classification:
    team: str
    priority: int


class BadAnswer(ValueError):
    """The provider answered, but not in the agreed shape. Retrying the same request will
    most likely give the same answer, so this is not a reason to retry."""


def parse_classification(answer: dict) -> Classification:
    try:
        data = json.loads(answer["choices"][0]["message"]["content"])
        team, priority = data["team"], int(data["priority"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise BadAnswer(f"not a classification: {error}") from None
    if team not in TEAMS or priority not in (1, 2, 3):
        raise BadAnswer(f"not a classification: {team!r}, {priority!r}")
    return Classification(team, priority)


def parse_draft(answer: dict) -> str:
    try:
        text = answer["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as error:
        raise BadAnswer(f"not a reply: {error}") from None
    if not text:
        raise BadAnswer("an empty reply")
    return text


def parse_embedding(answer: dict) -> list[float]:
    try:
        vector = [float(x) for x in answer["data"][0]["embedding"]]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise BadAnswer(f"not an embedding: {error}") from None
    if len(vector) != EMBED_DIMENSIONS:
        raise BadAnswer(f"an embedding with {len(vector)} numbers, not {EMBED_DIMENSIONS}")
    return vector


def usage(answer: dict) -> tuple[int, int]:
    """Tokens in and out, as the provider counted them."""
    u = answer.get("usage") or {}
    return int(u.get("prompt_tokens", 0)), int(u.get("completion_tokens", 0))
