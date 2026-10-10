"""The job queue in PostgreSQL: every SQL statement of the jobs, in one place (Module 4).

A job's life:

    submit -> queued -> running -> succeeded
                 ^         |-----> failed       (an error that a retry cannot fix)
                 |         |-----> dead_letter  (still failing after max_attempts: a person looks)
                 |---------|       (a retryable error: queued again, later: backoff + jitter)
    queued -> cancelled            (the caller cancelled it before a worker took it)

A worker takes a job with a lease (locked_until). If the worker stops without finishing,
the lease ends and another worker takes the job again: the job is DELIVERED TWICE. So the
work must be idempotent: doing it twice has the effect of doing it once (ai_runs has one
row per job and task, and a finished step is not called again).
"""

import random
from datetime import datetime

import psycopg

STATES = ("queued", "running", "succeeded", "failed", "cancelled", "dead_letter")
FINISHED = ("succeeded", "failed", "cancelled", "dead_letter")
JOB_COLUMNS = (
    "job_id, kind, ticket_id, actor, state, attempts, max_attempts, run_after, locked_by,"
    " locked_until, last_error, created_at, started_at, finished_at, updated_at"
)


class IdempotencyConflict(Exception):
    """The same Idempotency-Key came with a different request."""


def find_by_key(conn: psycopg.Connection, actor: str, key: str) -> dict | None:
    return conn.execute(
        f"SELECT {JOB_COLUMNS}, request_sha256 FROM jobs WHERE actor = %s AND idempotency_key = %s",
        (actor, key),
    ).fetchone()


def enqueue(
    conn: psycopg.Connection,
    ticket_id: str,
    actor: str,
    *,
    idempotency_key: str | None = None,
    request_sha256: str | None = None,
    max_attempts: int = 5,
) -> dict:
    """A new queued job. Call it in the same transaction as the ticket's insert."""
    return conn.execute(
        "INSERT INTO jobs (ticket_id, actor, idempotency_key, request_sha256, max_attempts)"
        f" VALUES (%s, %s, %s, %s, %s) RETURNING {JOB_COLUMNS}",
        (ticket_id, actor, idempotency_key, request_sha256, max_attempts),
    ).fetchone()


def get(conn: psycopg.Connection, job_id: int) -> dict | None:
    return conn.execute(f"SELECT {JOB_COLUMNS} FROM jobs WHERE job_id = %s", (job_id,)).fetchone()


def claim(conn: psycopg.Connection, worker: str, limit: int, lease_seconds: float) -> list[dict]:
    """Take up to `limit` jobs for this worker: queued jobs that may run now, and running jobs
    whose lease has ended (their worker stopped). SKIP LOCKED: rows that another worker is
    taking at this moment are skipped, not waited for."""
    return conn.execute(
        "UPDATE jobs SET state = 'running', attempts = attempts + 1, locked_by = %(worker)s,"
        " locked_until = now() + make_interval(secs => %(lease)s),"
        " started_at = coalesce(started_at, now()), updated_at = now()"
        " WHERE job_id IN ("
        "   SELECT job_id FROM jobs"
        "   WHERE ((state = 'queued' AND run_after <= now())"
        "      OR (state = 'running' AND locked_until < now()))"
        "     AND attempts < max_attempts"
        "   ORDER BY run_after, job_id LIMIT %(limit)s FOR UPDATE SKIP LOCKED)"
        f" RETURNING {JOB_COLUMNS}",
        {"worker": worker, "lease": lease_seconds, "limit": limit},
    ).fetchall()


def expired_without_attempts(conn: psycopg.Connection) -> int:
    """Running jobs whose lease ended and that have no attempt left: dead letters."""
    return conn.execute(
        "UPDATE jobs SET state = 'dead_letter', finished_at = now(), updated_at = now(),"
        " last_error = coalesce(last_error, 'the worker stopped during the last attempt'),"
        " locked_by = NULL, locked_until = NULL"
        " WHERE state = 'running' AND locked_until < now() AND attempts >= max_attempts"
    ).rowcount


def finish(
    conn: psycopg.Connection, job_id: int, worker: str, state: str, error: str | None = None
) -> bool:
    """Mark the job finished, only if this worker still holds it. False: another worker took
    it over (the lease ended), and its result counts."""
    assert state in FINISHED
    return (
        conn.execute(
            "UPDATE jobs SET state = %s, last_error = %s, finished_at = now(), updated_at = now(),"
            " locked_by = NULL, locked_until = NULL"
            " WHERE job_id = %s AND locked_by = %s AND state = 'running'",
            (state, error, job_id, worker),
        ).rowcount
        == 1
    )


def retry_later(
    conn: psycopg.Connection, job_id: int, worker: str, delay: float, error: str
) -> bool:
    """Back to the queue, to run again after `delay` seconds."""
    return (
        conn.execute(
            "UPDATE jobs SET state = 'queued', run_after = now() + make_interval(secs => %s),"
            " last_error = %s, locked_by = NULL, locked_until = NULL, updated_at = now()"
            " WHERE job_id = %s AND locked_by = %s AND state = 'running'",
            (delay, error, job_id, worker),
        ).rowcount
        == 1
    )


def release(conn: psycopg.Connection, job_id: int, worker: str, delay: float = 0.0) -> bool:
    """Give a job back without counting the attempt (Module 5): the worker is stopping
    (graceful shutdown), or the circuit to the provider is open."""
    return (
        conn.execute(
            "UPDATE jobs SET state = 'queued', attempts = attempts - 1,"
            " run_after = now() + make_interval(secs => %s),"
            " locked_by = NULL, locked_until = NULL, updated_at = now()"
            " WHERE job_id = %s AND locked_by = %s AND state = 'running'",
            (delay, job_id, worker),
        ).rowcount
        == 1
    )


def cancel(conn: psycopg.Connection, job_id: int) -> tuple[dict | None, bool]:
    """Cancel a queued job. A running or finished job does not change. (job, changed)"""
    changed = conn.execute(
        "UPDATE jobs SET state = 'cancelled', finished_at = now(), updated_at = now()"
        " WHERE job_id = %s AND state = 'queued'",
        (job_id,),
    ).rowcount
    return get(conn, job_id), changed == 1


def requeue(conn: psycopg.Connection, job_id: int) -> tuple[dict | None, bool]:
    """A person sends a dead letter back to the queue, with its attempts reset."""
    changed = conn.execute(
        "UPDATE jobs SET state = 'queued', attempts = 0, run_after = now(), finished_at = NULL,"
        " updated_at = now() WHERE job_id = %s AND state = 'dead_letter'",
        (job_id,),
    ).rowcount
    return get(conn, job_id), changed == 1


def stats(conn: psycopg.Connection) -> dict:
    """The numbers to watch (and to scale on): how many wait, how old the oldest is, how many
    finished in the last minute."""
    row = conn.execute(
        "SELECT"
        " count(*) FILTER (WHERE state = 'queued') AS queued,"
        " count(*) FILTER (WHERE state = 'queued' AND run_after <= now()) AS ready,"
        " count(*) FILTER (WHERE state = 'running') AS running,"
        " count(*) FILTER (WHERE state = 'dead_letter') AS dead_letter,"
        " count(*) FILTER (WHERE state = 'failed') AS failed,"
        " count(*) FILTER (WHERE state = 'succeeded' AND finished_at > now() - interval '1 minute')"
        "   AS succeeded_last_minute,"
        " coalesce(extract(epoch FROM now() - min(created_at) FILTER (WHERE state = 'queued')), 0)"
        "   AS oldest_queued_seconds"
        " FROM jobs WHERE state IN ('queued', 'running', 'dead_letter', 'failed')"
        " OR finished_at > now() - interval '1 minute'"
    ).fetchone()
    return {
        k: (round(float(v), 1) if k == "oldest_queued_seconds" else int(v)) for k, v in row.items()
    }


def queued_count(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT count(*) AS n FROM jobs WHERE state = 'queued'").fetchone()["n"]


def queued_ahead(conn: psycopg.Connection, job_id: int, run_after: datetime) -> int:
    return conn.execute(
        "SELECT count(*) AS n FROM jobs WHERE state = 'queued' AND (run_after, job_id) < (%s, %s)",
        (run_after, job_id),
    ).fetchone()["n"]


def backoff_seconds(attempt: int, base: float = 2.0, cap: float = 60.0, rng=random) -> float:
    """Exponential backoff with full jitter: a random wait between 0 and base * 2^(attempt-1)
    (at most `cap`). The randomness spreads out retries that failed at the same moment."""
    return rng.uniform(0, min(cap, base * 2 ** (attempt - 1)))
