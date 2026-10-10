"""New tickets: save the ticket and do its AI work (the scaling course, Module 1).

    POST /v1/tickets  {"customer_id": "C-0022", "subject": "...", "body": "..."}

For every new ticket, the API asks the AI provider three things, one after the other:
the team and priority (classify), a first reply for a person to check (draft_reply), and
a vector for similar-ticket search (embed). It answers when all three are done. A ticket
is saved only if all the AI work worked. The response has a Server-Timing header with the
time of each part (db, classify, draft_reply, embed).

INTAKE_MODE chooses how the request waits for the provider (Module 2):
- async (the default): an async endpoint awaits the provider, so one process serves many
  tickets at the same time. The AI work runs first, with no database connection; then one
  short transaction saves the ticket and the results.
- thread: the Module 1 version, kept for measuring. A normal function in one of the
  server's worker threads; it keeps a database connection for the whole request.
- blocking: a mistake, made on purpose to measure it. An async endpoint that calls the
  provider with the waiting client: while it waits, the whole server waits.
"""

import hashlib
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool

from ticket_api import ai, repository
from ticket_api.cache import Cache, embedding_key
from ticket_api.db import Database, DatabaseUnavailable
from ticket_api.models import AiRun, ErrorResponse, NewTicket, NewTicketResult
from ticket_api.prices import cost_usd
from ticket_api.provider import Provider, ProviderUnavailable
from ticket_api.security import require_api_key
from ticket_api.timing import Timer

EMBEDDING_TTL_SECONDS = 24 * 3600  # an embedding of the same text by the same model never changes

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


async def embed_cached(provider: Provider, cache: Cache | None, subject: str, body: str) -> tuple:
    """The embedding, from the shared cache when the same text was embedded before (Module 3).
    Returns (answer, ms, cached)."""
    key = embedding_key(ai.EMBED_MODEL, ai.EMBED_DIMENSIONS, ai.ticket_text(subject, body))
    started = time.perf_counter()
    if cache is not None:
        found = await cache.get(key)
        if found is not None:
            return found, (time.perf_counter() - started) * 1000, True
    answer, ms = await provider.acall("embeddings", ai.embed_request(subject, body))
    if cache is not None:
        await cache.set(key, answer, EMBEDDING_TTL_SECONDS)
    return answer, ms, False


async def do_ai_work_async(
    provider: Provider, subject: str, body: str, timer: Timer, cache: Cache | None = None
) -> dict:
    """The same three calls, awaited: while one ticket waits, the server works on others."""
    with timer("classify"):
        answer, ms = await provider.acall("chat/completions", ai.classify_request(subject, body))
    label = ai.parse_classification(answer)
    classify = run_record(
        "classify",
        ai.CLASSIFY_PROMPT,
        answer,
        ms,
        f'{{"team": "{label.team}", "priority": {label.priority}}}',
    )
    with timer("draft_reply"):
        answer, ms = await provider.acall("chat/completions", ai.draft_request(subject, body))
    draft = ai.parse_draft(answer)
    draft_run = run_record("draft_reply", ai.DRAFT_PROMPT, answer, ms, draft)
    with timer("embed"):
        answer, ms, cached = await embed_cached(provider, cache, subject, body)
    vector = ai.parse_embedding(answer)
    if cached:  # no call, no tokens, no cost
        answer = {**answer, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
    output = f"vector {ai.EMBEDDING_VERSION}" + (" (from the cache)" if cached else "")
    embed_run = run_record("embed", None, answer, ms, output)
    return {
        "label": label,
        "draft": draft,
        "vector": vector,
        "runs": [classify, draft_run, embed_run],
    }


def save_results(conn, ticket_id: str, new: NewTicket, work: dict) -> None:
    for run in work["runs"]:
        repository.save_ai_run(conn, ticket_id, run)
    repository.set_classification(conn, ticket_id, work["label"].team, work["label"].priority)
    source = hashlib.sha256(f"{new.subject}\n{new.body}".encode()).hexdigest()
    repository.save_embedding(conn, ticket_id, ai.EMBEDDING_VERSION, work["vector"], source)


def create_in_one_transaction(db: Database, provider: Provider, new: NewTicket, timer: Timer):
    """The Module 1 version: one transaction from the first insert to the last result, so the
    request keeps a database connection while it waits for the provider."""
    with db.connection() as conn:
        with timer("db"):
            ticket = repository.insert_ticket(
                conn, new.customer_id, new.subject, new.body, new.channel
            )
        work = do_ai_work(provider, new.subject, new.body, timer)
        with timer("db"):
            save_results(conn, ticket["ticket_id"], new, work)
    return ticket, work


def check_customer(db: Database, customer_id: str) -> None:
    with db.connection() as conn:
        if not repository.customer_exists(conn, customer_id):
            raise repository.NotFound(f"Customer {customer_id} does not exist.")


def save_new_ticket(db: Database, new: NewTicket, work: dict) -> dict:
    """One short transaction: the ticket and all its AI results."""
    with db.connection() as conn:
        ticket = repository.insert_ticket(conn, new.customer_id, new.subject, new.body, new.channel)
        save_results(conn, ticket["ticket_id"], new, work)
    return ticket


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
async def create_ticket(
    new: NewTicket,
    request: Request,
    response: Response,
    db: Annotated[Database, Depends(get_db)],
    provider: Annotated[Provider, Depends(get_provider)],
) -> NewTicketResult:
    timer = Timer()
    request.state.timer = timer
    mode = request.app.state.settings.intake_mode
    cache: Cache | None = request.app.state.cache
    if mode == "thread":
        ticket, work = await run_in_threadpool(create_in_one_transaction, db, provider, new, timer)
    else:
        with timer("db"):
            await run_in_threadpool(check_customer, db, new.customer_id)
        if mode == "blocking":
            # A mistake, on purpose: the waiting client inside an async endpoint.
            work = do_ai_work(provider, new.subject, new.body, timer)
        else:
            work = await do_ai_work_async(provider, new.subject, new.body, timer, cache)
        with timer("db"):
            ticket = await run_in_threadpool(save_new_ticket, db, new, work)
    if cache is not None:
        # The customer's latest tickets are part of their answers: those answers are old now.
        await cache.invalidate(f"customer:{new.customer_id}")
    response.headers["Server-Timing"] = timer.header()
    return NewTicketResult(
        **{**ticket, "team": work["label"].team, "priority": work["label"].priority},
        draft_reply=work["draft"],
        embedding_version=ai.EMBEDDING_VERSION,
        ai_runs=[AiRun(**{k: r[k] for k in AiRun.model_fields}) for r in work["runs"]],
    )
