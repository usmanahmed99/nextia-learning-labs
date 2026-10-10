"""New tickets: save the ticket and do its AI work (the scaling course, Module 1).

    POST /v1/tickets  {"customer_id": "C-0022", "subject": "...", "body": "..."}

For every new ticket, the API asks the AI provider three things, one after the other:
the team and priority (classify), a first reply for a person to check (draft_reply), and
a vector for similar-ticket search (embed). It answers when all three are done. A ticket
is saved only if all the AI work worked. The response has a Server-Timing header with the
time of each part (db, classify, draft_reply, embed).

INTAKE_MODE chooses how the request gets its AI work:
- queue (the default from Module 4): the ticket and a job are saved in one transaction,
  and the API answers 202 Accepted at once. A worker (python -m ticket_api.worker) does the
  AI work later; GET /v1/jobs/{id} shows the state and the result. An Idempotency-Key
  header makes a repeated request return the same ticket and job. When the queue is full
  (QUEUE_MAX), the API answers 503 with Retry-After; a caller that sends too much gets 429.
The other modes do the AI work during the request (Module 2):
- async: an async endpoint awaits the provider, so one process serves many
  tickets at the same time. The AI work runs first, with no database connection; then one
  short transaction saves the ticket and the results.
- thread: the Module 1 version, kept for measuring. A normal function in one of the
  server's worker threads; it keeps a database connection for the whole request.
- blocking: a mistake, made on purpose to measure it. An async endpoint that calls the
  provider with the waiting client: while it waits, the whole server waits.
"""

import hashlib
import json
import math
import time
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.concurrency import run_in_threadpool

from ticket_api import ai, jobs, ratelimit, repository
from ticket_api.cache import Cache, embedding_key
from ticket_api.db import Database, DatabaseUnavailable
from ticket_api.models import AiRun, ErrorResponse, NewTicket, NewTicketResult, TicketAccepted
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


async def invalidate_customer(cache: Cache | None, customer_id: str) -> None:
    if cache is not None:
        # The customer's latest tickets are part of their answers: those answers are old now.
        await cache.invalidate(f"customer:{customer_id}")


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


class QueueFull(Exception):
    def __init__(self, queued: int, retry_after: int):
        super().__init__(f"{queued} jobs are queued")
        self.queued = queued
        self.retry_after = retry_after


def wait_estimate(stats: dict, ahead: int) -> float | None:
    """Seconds until a job with `ahead` jobs before it starts, at last minute's pace."""
    per_second = stats["succeeded_last_minute"] / 60
    return round(ahead / per_second, 1) if per_second > 0 else None


def request_digest(new: NewTicket) -> str:
    return hashlib.sha256(json.dumps(new.model_dump(), sort_keys=True).encode()).hexdigest()


def accept(db: Database, new: NewTicket, actor: str, key: str | None, settings) -> tuple:
    """Save the ticket and its job in one transaction, or return the earlier result of the
    same Idempotency-Key. Returns (ticket_id, job, queued_ahead, stats, replayed)."""
    digest = request_digest(new)
    with db.connection() as conn:
        if key:
            earlier = jobs.find_by_key(conn, actor, key)
            if earlier is not None:
                if earlier["request_sha256"] != digest:
                    raise jobs.IdempotencyConflict(key)
                ahead = jobs.queued_ahead(conn, earlier["job_id"], earlier["run_after"])
                return earlier["ticket_id"], earlier, ahead, jobs.stats(conn), True
        stats = jobs.stats(conn)
        if stats["queued"] >= settings.queue_max:
            wait = wait_estimate(stats, stats["queued"])
            raise QueueFull(stats["queued"], min(300, max(1, math.ceil(wait or 30))))
        if not repository.customer_exists(conn, new.customer_id):
            raise repository.NotFound(f"Customer {new.customer_id} does not exist.")
        ticket = repository.insert_ticket(conn, new.customer_id, new.subject, new.body, new.channel)
        job = jobs.enqueue(
            conn,
            ticket["ticket_id"],
            actor,
            idempotency_key=key,
            request_sha256=digest,
            max_attempts=settings.job_max_attempts,
        )
        ahead = jobs.queued_ahead(conn, job["job_id"], job["run_after"])
    return ticket["ticket_id"], job, ahead, stats, False


def accept_once(db: Database, new: NewTicket, actor: str, key: str | None, settings) -> tuple:
    try:
        return accept(db, new, actor, key, settings)
    except psycopg.errors.UniqueViolation:
        # The same key arrived twice at the same moment: the other request saved it first.
        return accept(db, new, actor, key, settings)


@router.post(
    "",
    status_code=202,
    summary="Send a new ticket",
    description=(
        "Saves the ticket. With INTAKE_MODE=queue (the default) its AI work (classify, draft a "
        "reply, embed) waits in the queue: 202 and the job's URL. In the other modes the AI work "
        "is done during the request: 201 and the results."
    ),
    response_model=TicketAccepted | NewTicketResult,
    responses={
        201: {"model": NewTicketResult, "description": "INTAKE_MODE async, thread or blocking."},
        404: {"model": ErrorResponse, "description": "No such customer."},
        422: {
            "model": ErrorResponse,
            "description": "Not valid, or the Idempotency-Key was used for another request.",
        },
        429: {"model": ErrorResponse, "description": "Too many tickets from this caller."},
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
    idempotency_key: Annotated[str | None, Header(min_length=8, max_length=100)] = None,
):
    timer = Timer()
    request.state.timer = timer
    settings = request.app.state.settings
    mode = settings.intake_mode
    cache: Cache | None = request.app.state.cache
    actor = f"customer:{new.customer_id}"
    with timer("rate_limit"):
        await ratelimit.check(cache, actor, settings.rate_limit_per_minute)
    if mode == "queue":
        with timer("db"):
            ticket_id, job, ahead, stats, replayed = await run_in_threadpool(
                accept_once, db, new, actor, idempotency_key, settings
            )
        if replayed:
            response.headers["Idempotent-Replayed"] = "true"
        else:
            await invalidate_customer(cache, new.customer_id)
        url = f"/v1/jobs/{job['job_id']}"
        response.headers["Location"] = url
        response.headers["Server-Timing"] = timer.header()
        return TicketAccepted(
            ticket_id=ticket_id,
            job_id=job["job_id"],
            state=job["state"],
            status_url=url,
            queued_ahead=ahead,
            estimated_wait_seconds=wait_estimate(stats, ahead + 1),
        )
    provider = get_provider(request)
    response.status_code = 201
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
    await invalidate_customer(cache, new.customer_id)
    response.headers["Server-Timing"] = timer.header()
    return NewTicketResult(
        **{**ticket, "team": work["label"].team, "priority": work["label"].priority},
        draft_reply=work["draft"],
        embedding_version=ai.EMBEDDING_VERSION,
        ai_runs=[AiRun(**{k: r[k] for k in AiRun.model_fields}) for r in work["runs"]],
    )
