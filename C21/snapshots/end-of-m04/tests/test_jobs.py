"""The job queue and the worker (the scaling course, Module 4)."""

import asyncio
import random
from dataclasses import replace

import pytest
from conftest import TEST_SETTINGS
from fakes import fake_provider

from ticket_api import jobs
from ticket_api.worker import make_worker

TICKET = {"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments."}


def run_worker(db_url, provider=None, name="w1", **changes):
    settings = replace(TEST_SETTINGS, database_url=db_url, retry_base_seconds=0.0, **changes)
    worker = make_worker(settings, name=name, provider=provider or fake_provider())

    async def go():
        worker.db.open()
        try:
            await worker.drain()
        finally:
            worker.db.close()

    asyncio.run(go())
    return worker


def test_a_ticket_and_its_job_are_saved_together(api, conn):
    r = api.post("/v1/tickets", json=TICKET)
    assert r.status_code == 202
    body = r.json()
    assert r.headers["Location"] == body["status_url"] == f"/v1/jobs/{body['job_id']}"
    assert body["state"] == "queued" and body["queued_ahead"] == 0
    job = conn.execute("SELECT ticket_id, actor, state FROM jobs").fetchone()
    assert job == {"ticket_id": body["ticket_id"], "actor": "customer:C-0022", "state": "queued"}


def test_the_worker_does_the_work_and_the_job_has_the_result(api, db_url, conn):
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    worker = run_worker(db_url)
    assert worker.counts["succeeded"] == 1
    job = api.get(f"/v1/jobs/{job_id}").json()
    assert job["state"] == "succeeded" and job["attempts"] == 1
    assert job["result"]["team"] == "billing" and job["result"]["draft_reply"]
    assert job["result"]["embedding_version"] == "embed-small-384-v1"
    runs = conn.execute("SELECT task FROM ai_runs WHERE job_id = %s ORDER BY run_id", (job_id,))
    assert [r["task"] for r in runs] == ["classify", "draft_reply", "embed"]


def test_the_same_idempotency_key_gives_the_same_ticket(api, conn):
    h = {"Idempotency-Key": "order-LK-182074-first-try"}
    first = api.post("/v1/tickets", json=TICKET, headers=h)
    again = api.post("/v1/tickets", json=TICKET, headers=h)
    assert again.status_code == 202 and again.headers["Idempotent-Replayed"] == "true"
    assert again.json()["job_id"] == first.json()["job_id"]
    assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 1
    other = api.post("/v1/tickets", json={**TICKET, "body": "Something else."}, headers=h)
    assert other.status_code == 422 and other.json()["error"]["code"] == "idempotency_key_reused"


def test_a_job_delivered_twice_has_one_effect(api, db_url, conn):
    """Constructed: worker 1 takes the job and stops without finishing (its lease ends);
    worker 2 takes the same job again. One result per task, no second provider call."""
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    first = fake_provider()
    run_worker(db_url, provider=first)
    conn.execute(
        "UPDATE jobs SET state = 'running', locked_by = 'w1', locked_until = now() - interval"
        " '1 second', finished_at = NULL WHERE job_id = %s",
        (job_id,),
    )
    second = fake_provider()
    run_worker(db_url, provider=second, name="w2")
    runs = conn.execute("SELECT count(*) AS n FROM ai_runs WHERE job_id = %s", (job_id,))
    assert runs.fetchone()["n"] == 3
    assert len(first.calls) == 3 and len(second.calls) == 0
    job = conn.execute("SELECT state, attempts, locked_by FROM jobs WHERE job_id = %s", (job_id,))
    assert job.fetchone() == {"state": "succeeded", "attempts": 2, "locked_by": None}


def test_a_busy_provider_means_wait_without_losing_an_attempt(api, db_url, conn):
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    for _ in range(8):  # more than JOB_MAX_ATTEMPTS: over the quota is not the job's fault
        run_worker(db_url, provider=fake_provider(fail="quota"))
        conn.execute("UPDATE jobs SET run_after = now() WHERE state = 'queued'")
    job = conn.execute("SELECT state, attempts FROM jobs WHERE job_id = %s", (job_id,)).fetchone()
    assert job == {"state": "queued", "attempts": 0}
    run_worker(db_url, provider=fake_provider(fail="quota"))
    later = conn.execute("SELECT run_after > now() AS later FROM jobs WHERE job_id = %s", (job_id,))
    assert later.fetchone()["later"]  # it waits (the provider's hint: 0.6 s, or the backoff)


def test_after_the_last_attempt_the_job_is_a_dead_letter(make_api, db_url):
    api = make_api(job_max_attempts=3)
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    provider = fake_provider(fail="outage")
    run_worker(db_url, provider=provider)  # no wait between retries in the tests
    job = api.get(f"/v1/jobs/{job_id}").json()
    assert job["state"] == "dead_letter" and job["attempts"] == 3
    assert len(provider.calls) == 3  # bounded: 3 attempts, then a person looks
    again = api.post(f"/v1/jobs/{job_id}/retry").json()
    assert again["state"] == "queued" and again["attempts"] == 0


def test_a_bad_answer_fails_at_once(api, db_url):
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    run_worker(db_url, provider=fake_provider(fail="bad"))
    job = api.get(f"/v1/jobs/{job_id}").json()
    assert job["state"] == "failed" and job["attempts"] == 1
    assert job["last_error"].startswith("BadAnswer")


def test_cancel_a_queued_job(api, db_url):
    job_id = api.post("/v1/tickets", json=TICKET).json()["job_id"]
    assert api.post(f"/v1/jobs/{job_id}/cancel").json()["state"] == "cancelled"
    assert api.post(f"/v1/jobs/{job_id}/cancel").status_code == 409
    worker = run_worker(db_url)
    assert worker.counts["claimed"] == 0


def test_a_full_queue_refuses_with_retry_after(make_api, conn):
    api = make_api(queue_max=2)
    assert [api.post("/v1/tickets", json=TICKET).status_code for _ in range(3)] == [202, 202, 503]
    r = api.post("/v1/tickets", json=TICKET)
    assert r.json()["error"]["code"] == "queue_full" and int(r.headers["Retry-After"]) >= 1
    assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 2


def test_too_many_tickets_from_one_caller_get_429(make_api, cache_url):
    api = make_api(cache_url=cache_url, rate_limit_per_minute=3)
    codes = [api.post("/v1/tickets", json=TICKET).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]
    other = api.post("/v1/tickets", json={**TICKET, "customer_id": "C-0003"})
    assert other.status_code == 202  # the limit is per caller


def test_queue_numbers(api, db_url):
    for _ in range(3):
        api.post("/v1/tickets", json=TICKET)
    stats = api.get("/v1/queue").json()
    assert stats["queued"] == 3 and stats["ready"] == 3 and stats["running"] == 0
    run_worker(db_url)
    stats = api.get("/v1/queue").json()
    assert stats["queued"] == 0 and stats["succeeded_last_minute"] == 3


def test_two_workers_never_take_the_same_job(api, db_url, conn):
    for _ in range(6):
        api.post("/v1/tickets", json=TICKET)
    import psycopg
    from psycopg.rows import dict_row

    with (
        psycopg.connect(db_url, row_factory=dict_row) as a,
        psycopg.connect(db_url, row_factory=dict_row) as b,
    ):
        got_a = jobs.claim(a, "a", 4, 30)  # a's transaction is still open: rows locked
        got_b = jobs.claim(b, "b", 4, 30)  # SKIP LOCKED: b takes the others, does not wait
        assert len(got_a) == 4 and len(got_b) == 2
        assert not {j["job_id"] for j in got_a} & {j["job_id"] for j in got_b}


@pytest.mark.parametrize("attempt,cap", [(1, 2.0), (3, 8.0), (10, 60.0)])
def test_backoff_has_jitter_and_a_cap(attempt, cap):
    rng = random.Random(1)
    waits = [jobs.backoff_seconds(attempt, rng=rng) for _ in range(200)]
    assert 0 <= min(waits) and max(waits) <= cap
    assert len(set(round(w, 3) for w in waits)) > 150  # spread out, not all the same
