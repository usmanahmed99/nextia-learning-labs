"""How a new ticket waits for the AI provider (the scaling course, Module 2).

The fake provider takes 0.2 s per call (3 calls per ticket), and the tests send 4 tickets at
the same time to one app, in one process, as a real server would.
"""

import asyncio
import time
from dataclasses import replace

import httpx
import pytest
from conftest import TEST_SETTINGS
from fakes import fake_provider

from ticket_api.config import SettingsError, load_settings
from ticket_api.main import create_app

TICKET = {"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments."}


async def send_together(app, n: int) -> tuple[float, list[int]]:
    app.state.db.open()
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = time.perf_counter()
            responses = await asyncio.gather(
                *(client.post("/v1/tickets", json=TICKET) for _ in range(n))
            )
            return time.perf_counter() - started, [r.status_code for r in responses]
    finally:
        app.state.db.close()


def make(db_url, mode: str, delay: float = 0.2, **changes):
    settings = replace(TEST_SETTINGS, database_url=db_url, intake_mode=mode, **changes)
    return create_app(settings, provider=fake_provider(delay=delay))


@pytest.mark.parametrize("mode", ["async", "thread", "blocking"])
def test_every_mode_gives_the_same_ticket(db_url, mode):
    seconds, statuses = asyncio.run(send_together(make(db_url, mode, delay=0), 1))
    assert statuses == [201]


def test_async_waits_together(db_url):
    seconds, statuses = asyncio.run(send_together(make(db_url, "async"), 4))
    assert statuses == [201] * 4
    assert seconds < 1.2  # about 0.6 s: the four tickets wait for the provider together


def test_a_blocking_call_stalls_the_whole_server(db_url):
    seconds, statuses = asyncio.run(send_together(make(db_url, "blocking"), 4))
    assert statuses == [201] * 4
    assert seconds > 2.2  # about 2.4 s: one ticket after the other


def test_threads_also_wait_together(db_url):
    seconds, statuses = asyncio.run(send_together(make(db_url, "thread"), 4))
    assert statuses == [201] * 4
    assert seconds < 1.2


def test_a_connection_held_during_the_ai_work_runs_out(db_url):
    """One connection in the pool. The Module 1 version keeps it for the whole request, so
    the second ticket waits for it, longer than DB_POOL_TIMEOUT: 503 database_busy."""
    tight = {"db_pool_min": 1, "db_pool_max": 1, "db_pool_timeout": 0.3}
    _, statuses = asyncio.run(send_together(make(db_url, "thread", **tight), 2))
    assert sorted(statuses) == [201, 503]
    _, statuses = asyncio.run(send_together(make(db_url, "async", **tight), 2))
    assert statuses == [201, 201]  # the connection is used only for milliseconds


def test_max_concurrency_limits_calls_in_flight():
    provider = fake_provider(delay=0.1, max_concurrency=2)

    async def six():
        started = time.perf_counter()
        await asyncio.gather(
            *(
                provider.acall("embeddings", {"model": "embed-small", "input": "a"})
                for _ in range(6)
            )
        )
        return time.perf_counter() - started

    assert 0.28 < asyncio.run(six()) < 0.6  # 3 rounds of 2


def test_intake_mode_is_checked(monkeypatch):
    monkeypatch.setenv("INTAKE_MODE", "fast")
    with pytest.raises(SettingsError):
        load_settings()
