"""The simulated AI provider: shape of the answers, times from the recordings, the quota."""

import statistics

from fastapi.testclient import TestClient

from simulator import model
from simulator.app import Settings, create_app
from simulator.quota import Quota
from ticket_api import ai


def make(monkeypatch, **env) -> TestClient:
    monkeypatch.setenv("SIM_SPEED", "0")  # no waiting in the tests
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return TestClient(create_app(Settings()))


def test_answers_have_the_openai_shape(monkeypatch):
    sim = make(monkeypatch)
    r = sim.post("/v1/chat/completions", json=ai.classify_request("Charged twice", "refund please"))
    assert r.status_code == 200 and r.headers["X-Simulated"] == "true"
    assert ai.parse_classification(r.json()).team == "billing"
    assert r.json()["model"] == "chat-small (simulated)"
    r = sim.post("/v1/embeddings", json=ai.embed_request("Charged twice", "refund please"))
    assert len(ai.parse_embedding(r.json())) == 384


def test_a_recorded_ticket_gets_its_recorded_answer():
    text = ai.ticket_text(
        "Charged twice for order LK-182074",
        "My card was charged two times for order LK-182074, 449.00 dollars each time. "
        "Please refund one of the payments.",
    )
    body = ai.draft_request("x", "y")
    body["messages"][1]["content"] = text
    assert "LK-182074" in model.chat_answer(body, "chat-small")["choices"][0]["message"]["content"]


def test_times_come_from_the_recordings():
    import random

    rng = random.Random(1)
    times = [model.sample_latency_ms("draft_reply", rng) for _ in range(2000)]
    recorded = model.CALIBRATION["latency_ms"]["draft_reply"]
    assert min(recorded) <= min(times) and max(times) <= max(recorded)
    assert abs(statistics.median(times) - statistics.median(recorded)) < 60


def test_similar_texts_get_similar_vectors():
    a = model.embedding("my parcel was not delivered")
    b = model.embedding("the parcel was not delivered yet")
    c = model.embedding("reset my password please")
    dot = lambda x, y: sum(p * q for p, q in zip(x, y, strict=True))  # noqa: E731
    assert dot(a, b) > dot(a, c)


def test_the_quota_refuses_with_two_hints():
    now = [0.0]
    q = Quota(rpm=6, tpm=None, burst_seconds=60, clock=lambda: now[0])
    assert [q.try_take(1) for _ in range(6)] == [None] * 6
    wait = q.try_take(1)
    assert wait == 10.0  # one request comes back every 10 seconds
    now[0] = 10.0
    assert q.try_take(1) is None


def test_quota_mode_sends_429_with_retry_after(monkeypatch):
    sim = make(monkeypatch, SIM_MODE="quota")
    statuses = [
        sim.post("/v1/chat/completions", json=ai.draft_request("a", "b")).status_code
        for _ in range(15)
    ]
    assert statuses.count(200) == 10 and statuses.count(429) == 5
    r = sim.post("/v1/chat/completions", json=ai.draft_request("a", "b"))
    assert r.headers["Retry-After"] == "30" and int(r.headers["retry-after-ms"]) > 0


def test_outage_mode_and_stats(monkeypatch):
    sim = make(monkeypatch)
    sim.post("/admin/mode", json={"mode": "outage"})
    assert sim.post("/v1/embeddings", json=ai.embed_request("a", "b")).status_code == 503
    assert sim.get("/admin/stats").json()["calls"] == {"embed": {"503": 1}}
    sim.post("/admin/reset")
    assert sim.get("/admin/stats").json()["mode"] == "normal"
