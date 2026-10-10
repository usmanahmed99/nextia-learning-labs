"""The shared cache (the scaling course, Module 3): right keys, invalidation, failures."""

import asyncio
from dataclasses import replace

import httpx
from conftest import TEST_SETTINGS
from fakes import fake_provider

from ticket_api import answers, cache
from ticket_api.main import create_app

Q = {"question": "Where is my parcel and how do I track it?"}


def test_a_key_holds_everything_that_changes_the_answer():
    v = {"prompt": "answer-v1", "model": "chat-small", "docs": "abc"}
    a = cache.answer_key("customer:C-0001", 0, "Where is my parcel?", v)
    assert a == cache.answer_key("customer:C-0001", 0, "  where IS my   parcel?", v)
    assert a != cache.answer_key("customer:C-0002", 0, "Where is my parcel?", v)
    assert a != cache.answer_key("staff", 0, "Where is my parcel?", v)
    assert a != cache.answer_key("customer:C-0001", 1, "Where is my parcel?", v)
    assert a != cache.answer_key("customer:C-0001", 0, "Where is my parcel?", {**v, "docs": "abd"})
    assert ":customer:C-0001:g0:" in a


def test_hit_after_miss_and_one_provider_call(make_api, cache_url):
    provider = fake_provider()
    api = make_api(provider=provider, cache_url=cache_url)
    first = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0003"})
    second = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0003"})
    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("miss", "hit")
    assert first.json()["answer"] == second.json()["answer"] and second.json()["cached"]
    assert provider.calls.paths == ["chat/completions"]


def test_one_customers_answer_is_never_served_to_another(make_api, cache_url, conn):
    """The completion check of Module 3: the same question, two customers, two answers."""
    api = make_api(cache_url=cache_url)
    a = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0003"}).json()
    b_response = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0022"})
    b = b_response.json()
    a_tickets = {
        r["ticket_id"]
        for r in conn.execute("SELECT ticket_id FROM tickets WHERE customer_id = 'C-0003'")
    }
    assert b_response.headers["X-Cache"] == "miss"
    assert any(t in a["answer"] for t in a_tickets)
    assert not any(t in b["answer"] for t in a_tickets)
    assert (a["scope"], b["scope"]) == ("customer:C-0003", "customer:C-0022")


def test_a_key_without_the_scope_leaks(make_api, cache_url, monkeypatch, conn):
    """Constructed: the wrong key (the question only). Customer C-0022 gets C-0003's answer."""
    monkeypatch.setattr(
        answers, "answer_key", lambda scope, gen, question, versions: "ta:wrong:" + question
    )
    api = make_api(cache_url=cache_url)
    a = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0003"}).json()
    b = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0022"})
    assert b.headers["X-Cache"] == "hit"
    assert b.json()["answer"] == a["answer"] and b.json()["scope"] == "customer:C-0003"


def test_staff_and_customers_have_different_answers(make_api, cache_url):
    api = make_api(cache_url=cache_url)
    q = {"question": "How do we approve a manual refund or goodwill credit?"}
    staff = api.post("/v1/answers", json=q).json()
    customer = api.post("/v1/answers", json=q, headers={"X-Customer-ID": "C-0003"}).json()
    assert "refund-approval-procedure" in staff["sources"]  # a staff-only document
    assert "refund-approval-procedure" not in customer["sources"]


def test_a_new_ticket_makes_the_customers_answers_old(make_api, cache_url):
    api = make_api(cache_url=cache_url)
    h = {"X-Customer-ID": "C-0003"}
    api.post("/v1/answers", json=Q, headers=h)
    assert api.post("/v1/answers", json=Q, headers=h).headers["X-Cache"] == "hit"
    new = api.post(
        "/v1/tickets",
        json={
            "customer_id": "C-0003",
            "subject": "Lost parcel",
            "body": "My parcel did not arrive.",
        },
    )
    after = api.post("/v1/answers", json=Q, headers=h)
    assert after.headers["X-Cache"] == "miss"
    assert new.json()["ticket_id"] in after.json()["answer"]


def test_a_new_message_makes_the_customers_answers_old(make_api, cache_url):
    api = make_api(cache_url=cache_url)
    h = {"X-Customer-ID": "C-0003"}
    api.post("/v1/answers", json=Q, headers=h)
    ticket = api.get("/v1/tickets?customer_id=C-0003&limit=1").json()["items"][0]["ticket_id"]
    api.post(f"/v1/tickets/{ticket}/messages", json={"author": "customer", "body": "Any news?"})
    assert api.post("/v1/answers", json=Q, headers=h).headers["X-Cache"] == "miss"


def test_the_api_works_when_the_cache_is_down(make_api):
    api = make_api(cache_url="redis://127.0.0.1:1/0")  # nothing listens there
    r = api.post("/v1/answers", json=Q, headers={"X-Customer-ID": "C-0003"})
    assert r.status_code == 200 and r.headers["X-Cache"] == "off"


def test_the_same_text_is_embedded_once(make_api, cache_url):
    provider = fake_provider()
    api = make_api(provider=provider, cache_url=cache_url)
    t = {"customer_id": "C-0003", "subject": "Lost parcel", "body": "It did not arrive."}
    api.post("/v1/tickets", json=t)
    second = api.post("/v1/tickets", json=t).json()
    assert provider.calls.paths.count("embeddings") == 1
    embed = second["ai_runs"][2]
    assert (embed["tokens_in"], embed["cost_usd"]) == (0, 0)


def send_together(db_url, cache_url, n, guard):
    settings = replace(
        TEST_SETTINGS, database_url=db_url, cache_url=cache_url, cache_stampede_guard=guard
    )
    provider = fake_provider(delay=0.3)
    app = create_app(settings, provider=provider)

    async def go():
        app.state.db.open()
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
                rs = await asyncio.gather(*(c.post("/v1/answers", json=Q) for _ in range(n)))
            await app.state.cache.close()
            return [r.headers["X-Cache"] for r in rs]
        finally:
            app.state.db.close()

    return asyncio.run(go()), len(provider.calls)


def test_a_stampede_without_a_guard_calls_the_provider_for_every_request(db_url, cache_url):
    statuses, calls = send_together(db_url, cache_url, 10, guard=False)
    assert calls == 10 and statuses == ["miss"] * 10


def test_the_guard_lets_one_request_compute(db_url, cache_url):
    statuses, calls = send_together(db_url, cache_url, 10, guard=True)
    assert calls == 1
    assert sorted(statuses) == ["miss"] + ["wait"] * 9
