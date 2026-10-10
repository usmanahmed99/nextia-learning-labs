"""New tickets: save the ticket and do its AI work (the scaling course, Module 1).

    POST /v1/tickets  {"customer_id": "C-0022", "subject": "...", "body": "..."}

For every new ticket, the API asks the AI provider three things, one after the other:
the team and priority (classify), a first reply for a person to check (draft_reply), and
a vector for similar-ticket search (embed). It answers when all three are done.

This first version does everything inside one database transaction, so a ticket is saved
only if all the AI work worked. The response has a Server-Timing header with the time of
each part (db, classify, draft_reply, embed).
"""

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ticket_api import ai, repository
from ticket_api.db import Database, DatabaseUnavailable
from ticket_api.models import AiRun, ErrorResponse, NewTicket, NewTicketResult
from ticket_api.prices import cost_usd
from ticket_api.provider import Provider, ProviderUnavailable
from ticket_api.security import require_api_key
from ticket_api.timing import Timer

router = APIRouter(prefix="/v1/tickets", tags=["tickets"], dependencies=[Depends(require_api_key)])


def get_db(request: Request) -> Database:
    db = request.app.state.db
    if db is None:
        raise DatabaseUnavailable("DATABASE_URL is not set")
    return db


def get_provider(request: Request) -> Provider:
    provider = request.app.state.provider
    if provider is None:
        raise ProviderUnavailable("PROVIDER_URL is not set")
    return provider


def run_record(task: str, prompt: str | None, answer: dict, ms: float, output: str) -> dict:
    tokens_in, tokens_out = ai.usage(answer)
    requested = ai.EMBED_MODEL if task == "embed" else ai.CHAT_MODEL
    return {
        "task": task,
        "model": answer.get("model", requested),
        "prompt_version": prompt,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost_usd(requested, tokens_in, tokens_out),
        "latency_ms": round(ms),
        "status": "ok",
        "output": output,
    }


def do_ai_work(provider: Provider, subject: str, body: str, timer: Timer) -> dict:
    """Call the provider three times, one after the other. Raises a ProviderError on failure."""
    with timer("classify"):
        answer, ms = provider.call("chat/completions", ai.classify_request(subject, body))
    label = ai.parse_classification(answer)
    classify = run_record(
        "classify",
        ai.CLASSIFY_PROMPT,
        answer,
        ms,
        f'{{"team": "{label.team}", "priority": {label.priority}}}',
    )
    with timer("draft_reply"):
        answer, ms = provider.call("chat/completions", ai.draft_request(subject, body))
    draft = ai.parse_draft(answer)
    draft_run = run_record("draft_reply", ai.DRAFT_PROMPT, answer, ms, draft)
    with timer("embed"):
        answer, ms = provider.call("embeddings", ai.embed_request(subject, body))
    vector = ai.parse_embedding(answer)
    embed_run = run_record("embed", None, answer, ms, f"vector {ai.EMBEDDING_VERSION}")
    return {
        "label": label,
        "draft": draft,
        "vector": vector,
        "runs": [classify, draft_run, embed_run],
    }


@router.post(
    "",
    status_code=201,
    summary="Send a new ticket",
    description="Saves the ticket and does its AI work: classify, draft a reply, embed.",
    responses={
        404: {"model": ErrorResponse, "description": "No such customer."},
        502: {
            "model": ErrorResponse,
            "description": "The AI provider gave an answer that is not valid.",
        },
        503: {
            "model": ErrorResponse,
            "description": "The AI provider or the database is not available.",
        },
    },
)
def create_ticket(
    new: NewTicket,
    request: Request,
    response: Response,
    db: Annotated[Database, Depends(get_db)],
    provider: Annotated[Provider, Depends(get_provider)],
) -> NewTicketResult:
    timer = Timer()
    request.state.timer = timer
    with db.connection() as conn:  # one transaction: the ticket and all its AI results, or nothing
        with timer("db"):
            ticket = repository.insert_ticket(
                conn, new.customer_id, new.subject, new.body, new.channel
            )
        work = do_ai_work(provider, new.subject, new.body, timer)
        with timer("db"):
            tid = ticket["ticket_id"]
            for run in work["runs"]:
                repository.save_ai_run(conn, tid, run)
            repository.set_classification(conn, tid, work["label"].team, work["label"].priority)
            source = hashlib.sha256(f"{new.subject}\n{new.body}".encode()).hexdigest()
            repository.save_embedding(conn, tid, ai.EMBEDDING_VERSION, work["vector"], source)
    response.headers["Server-Timing"] = timer.header()
    return NewTicketResult(
        **{**ticket, "team": work["label"].team, "priority": work["label"].priority},
        draft_reply=work["draft"],
        embedding_version=ai.EMBEDDING_VERSION,
        ai_runs=[AiRun(**{k: r[k] for k in AiRun.model_fields}) for r in work["runs"]],
    )
