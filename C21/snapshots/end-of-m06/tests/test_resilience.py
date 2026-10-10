"""Failure containment and graceful shutdown (the scaling course, Module 5)."""

import asyncio
from dataclasses import replace

import pytest
from conftest import TEST_SETTINGS
from fakes import fake_provider

from ticket_api.provider import ProviderUnavailable
from ticket_api.resilience import BreakerOpen, CircuitBreaker, RetryBudget
from ticket_api.worker import make_worker

TICKET = {"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments."}
EMBED = {"model": "embed-small", "input": "a"}


def test_the_breaker_opens_fails_fast_and_tries_again_later():
    now = [0.0]
    b = CircuitBreaker(failures=3, open_seconds=30, clock=lambda: now[0])
    for _ in range(3):
        b.before_call()
        b.failure()
    assert b.state == "open"
    with pytest.raises(BreakerOpen) as e:
        b.before_call()
    assert e.value.retry_after == 30
    now[0] = 31
    b.before_call()  # half-open: one trial call
    assert b.state == "half_open"
    with pytest.raises(BreakerOpen):
        b.before_call()  # only one trial at a time
    b.success()
    assert b.state == "closed"


def test_a_failed_trial_opens_the_breaker_again():
    now = [0.0]
    b = CircuitBreaker(failures=1, open_seconds=10, clock=lambda: now[0])
    b.failure()
    now[0] = 11
    b.before_call()
    b.failure()
    assert b.state == "open" and b.opened_count == 2


def test_the_retry_budget_allows_a_few_retries_only():
    budget = RetryBudget(ratio=0.1, window=10, minimum=3, clock=lambda: 0.0)
    for _ in range(100):
        budget.record_call()
    allowed = sum(budget.can_retry() for _ in range(50))
    assert allowed == 10 and budget.refused == 40


def test_retries_during_an_outage_stay_within_the_budget():
    provider = fake_provider(fail="outage", retries=2, budget=RetryBudget(ratio=0.1, minimum=3))

    async def many():
        for _ in range(50):
            with pytest.raises(ProviderUnavailable):
                await provider.acall("embeddings", EMBED)

    asyncio.run(many())
    assert len(provider.calls) <= 50 + 8  # without the budget: 150 calls


def test_with_a_breaker_most_calls_are_never_made():
    provider = fake_provider(fail="outage", breaker=CircuitBreaker(failures=5, open_seconds=30))

    async def many():
        for _ in range(50):
            with pytest.raises((ProviderUnavailable, BreakerOpen)):
                await provider.acall("embeddings", EMBED)

    asyncio.run(many())
    assert len(provider.calls) == 5


def worker_for(db_url, provider, **changes):
    settings = replace(TEST_SETTINGS, database_url=db_url, retry_base_seconds=0.0, **changes)
    return make_worker(settings, name="w1", provider=provider)


def test_jobs_wait_while_the_breaker_is_open(api, db_url, conn):
    for _ in range(10):
        api.post("/v1/tickets", json=TICKET)
    provider = fake_provider(fail="outage", breaker=CircuitBreaker(failures=3, open_seconds=60))
    worker = worker_for(db_url, provider, worker_concurrency=1)

    async def go():
        worker.db.open()
        try:
            await worker.drain()
        finally:
            worker.db.close()

    asyncio.run(go())
    assert len(provider.calls) == 3  # then the circuit is open: no more calls
    states = conn.execute("SELECT state, count(*) AS n FROM jobs GROUP BY state").fetchall()
    assert states == [{"state": "queued", "n": 10}]  # nothing burnt its attempts: no dead letter
    waiting = conn.execute("SELECT min(run_after - now()) AS w FROM jobs WHERE attempts = 0")
    assert waiting.fetchone()["w"].total_seconds() > 50


def run_and_stop(db_url, drain_seconds: float, stop_after: float):
    provider = fake_provider(delay=0.4)  # 1.2 s per job
    worker = worker_for(db_url, provider, worker_concurrency=2, worker_drain_seconds=drain_seconds)

    async def go():
        worker.db.open()
        stop = asyncio.Event()
        try:
            runner = asyncio.create_task(worker.run_forever(stop))
            await asyncio.sleep(stop_after)
            stop.set()  # what SIGTERM does
            await runner
        finally:
            worker.db.close()

    asyncio.run(go())
    return worker


def test_graceful_shutdown_finishes_the_running_jobs(api, db_url, conn):
    for _ in range(4):
        api.post("/v1/tickets", json=TICKET)
    worker = run_and_stop(db_url, drain_seconds=5, stop_after=0.3)
    assert worker.counts["claimed"] == 2 and worker.counts["succeeded"] == 2
    rows = conn.execute("SELECT state, count(*) AS n FROM jobs GROUP BY state").fetchall()
    states = {r["state"]: r["n"] for r in rows}
    assert states == {"succeeded": 2, "queued": 2}


def test_jobs_that_cannot_finish_in_time_go_back_to_the_queue(api, db_url, conn):
    for _ in range(2):
        api.post("/v1/tickets", json=TICKET)
    worker = run_and_stop(db_url, drain_seconds=0.2, stop_after=0.3)
    assert worker.counts["released"] == 2
    rows = conn.execute("SELECT state, attempts, locked_by FROM jobs").fetchall()
    assert rows == [{"state": "queued", "attempts": 0, "locked_by": None}] * 2


def test_the_api_fails_fast_while_the_breaker_is_open(make_api):
    provider = fake_provider(fail="outage", breaker=CircuitBreaker(failures=2, open_seconds=30))
    api = make_api(provider=provider)
    q = {"question": "How do I return a damaged item?"}
    codes = [api.post("/v1/answers", json=q).status_code for _ in range(4)]
    assert codes == [503] * 4 and len(provider.calls) == 2
    r = api.post("/v1/answers", json=q)
    assert r.json()["error"]["code"] == "ai_unavailable" and int(r.headers["Retry-After"]) > 25
