"""Answers to questions, with a shared cache (the scaling course, Module 3).

    POST /v1/answers  {"question": "How do I return a damaged item?"}
    X-Customer-ID: C-0022      (the shop's website, for a signed-in customer)
    (no X-Customer-ID)         (the help desk's own tool: staff)

The answer depends on WHO asks. A customer's answer may use public documents and that
customer's own tickets; staff answers may also use staff-only documents. So the caller's
identity scope is part of the cache key: "customer:C-0022" or "staff".

Here a header names the caller, and the API key proves that the request comes from one of
Larkfield's own apps. The authentication course replaces the header with a real sign-in.

The response says what the cache did (X-Cache): hit, miss, wait (another request was
computing the same answer, and this one used its result) or off (the cache is not set up,
or does not answer).
"""

import asyncio
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from ticket_api import ai, repository
from ticket_api.cache import Cache, answer_key
from ticket_api.db import Database
from ticket_api.intake import get_db, get_provider
from ticket_api.models import ErrorResponse
from ticket_api.provider import Provider
from ticket_api.security import require_api_key
from ticket_api.timing import Timer

router = APIRouter(prefix="/v1/answers", tags=["answers"], dependencies=[Depends(require_api_key)])


class Question(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"examples": [{"question": "How do I return a damaged item?"}]},
    )
    question: str = Field(min_length=3, max_length=500)


class Answer(BaseModel):
    answer: str
    scope: str = Field(description='Whose answer this is: "customer:<id>" or "staff".')
    sources: list[str] = Field(description="The documents the answer used.")
    cached: bool


def scope_of(customer_id: str | None) -> str:
    return f"customer:{customer_id}" if customer_id else "staff"


def context(db: Database, question: str, customer_id: str | None) -> dict:
    with db.connection() as conn:
        if customer_id and not repository.customer_exists(conn, customer_id):
            raise repository.NotFound(f"Customer {customer_id} does not exist.")
        access = ["public"] if customer_id else ["public", "staff"]
        return {
            "documents": repository.search_documents(conn, question, access),
            "tickets": repository.latest_tickets(conn, customer_id) if customer_id else [],
            "docs_version": repository.documents_version(conn),
        }


async def compute(provider: Provider, question: str, ctx: dict, scope: str) -> dict:
    answer, _ = await provider.acall(
        "chat/completions", ai.answer_request(question, ctx["documents"], ctx["tickets"])
    )
    return {
        "answer": ai.parse_draft(answer),
        "scope": scope,
        "sources": [d["doc_id"] for d in ctx["documents"]],
    }


async def wait_for(cache: Cache, key: str, seconds: float) -> dict | None:
    """Another request is computing this answer: wait for its result, a little at a time."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        await asyncio.sleep(0.05)
        found = await cache.get(key)
        if found is not None:
            return found
    return None


@router.post(
    "",
    summary="Answer a question",
    responses={
        404: {"model": ErrorResponse, "description": "No such customer."},
        503: {"model": ErrorResponse, "description": "The AI provider or the database is busy."},
    },
)
async def answer_question(
    q: Question,
    request: Request,
    response: Response,
    db: Annotated[Database, Depends(get_db)],
    provider: Annotated[Provider, Depends(get_provider)],
    x_customer_id: Annotated[str | None, Header(pattern=r"^C-[0-9]{4,5}$")] = None,
) -> Answer:
    settings = request.app.state.settings
    cache: Cache | None = request.app.state.cache
    timer = Timer()
    request.state.timer = timer
    scope = scope_of(x_customer_id)
    with timer("db"):
        ctx = await run_in_threadpool(context, db, q.question, x_customer_id)
    status, result, key = "off", None, None
    if cache is not None and cache.available():
        versions = {"prompt": ai.ANSWER_PROMPT, "model": ai.CHAT_MODEL, "docs": ctx["docs_version"]}
        with timer("cache"):
            key = answer_key(scope, await cache.generation(scope), q.question, versions)
            result = await cache.get(key)
        status = "hit" if result is not None else ("miss" if cache.available() else "off")
    if result is None:
        token = None
        if status == "miss" and settings.cache_stampede_guard:
            token = await cache.lock(key, settings.cache_lock_seconds)
            if token is None and cache.available():
                with timer("cache_wait"):
                    result = await wait_for(cache, key, settings.cache_lock_seconds)
                status = "wait" if result is not None else "miss"
        if result is None:
            try:
                with timer("answer"):
                    result = await compute(provider, q.question, ctx, scope)
                if status in ("miss", "wait"):
                    await cache.set(key, result, settings.cache_ttl_seconds)
            finally:
                if token is not None:
                    await cache.unlock(key, token)
    response.headers["X-Cache"] = status
    response.headers["Server-Timing"] = timer.header()
    return Answer(**result, cached=status in ("hit", "wait"))
