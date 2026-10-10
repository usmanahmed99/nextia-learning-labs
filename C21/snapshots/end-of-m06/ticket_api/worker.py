"""The worker: takes queued jobs and does their AI work (the scaling course, Module 4).

    python -m ticket_api.worker                 run until Ctrl+C
    python -m ticket_api.worker --once          take what is queued now, then stop
    python -m ticket_api.worker --concurrency 8 up to 8 jobs at the same time

One job = the AI work of one ticket, in three steps (classify, draft_reply, embed). Each
step's result is saved as soon as it is made, with the job's ID: if the job is delivered
again (a worker stopped, its lease ended), the steps that are done are not called again,
and no result is saved twice.

Errors:
- the provider is over its quota (429): the job waits (the provider's hint or a growing
  backoff, whichever is longer) and does not lose an attempt: it is not the job's fault;
- the provider is down (5xx) or too slow (timeout): retry later, with exponential backoff
  and jitter, at most JOB_MAX_ATTEMPTS attempts; then the job is a dead letter, for a
  person to look at.
- the provider refused the request or gave an answer that is not valid: failed at once (the
  same request would fail again).
- the circuit breaker is open (Module 5): the job goes back to the queue until the circuit
  may close, and the attempt does not count.

Stopping (Module 5): on SIGTERM or Ctrl+C the worker takes no new job, lets the running ones
finish for up to WORKER_DRAIN_SECONDS, and gives the rest back to the queue (not counted
as an attempt). A worker that is killed (SIGKILL, a crash, a lost machine) cannot do this:
its jobs stay "running" until their lease ends, then another worker takes them again.
"""

import argparse
import asyncio
import hashlib
import logging
import os
import signal
import socket
import sys
import time

from ticket_api import ai, jobs, repository
from ticket_api.cache import Cache, make_cache
from ticket_api.config import Settings, SettingsError, load_settings
from ticket_api.db import Database
from ticket_api.intake import embed_cached, run_record
from ticket_api.provider import (
    Provider,
    ProviderError,
    ProviderRateLimited,
    ProviderRejected,
    make_provider,
)
from ticket_api.resilience import BreakerOpen

logger = logging.getLogger("ticket_api.worker")


class Worker:
    def __init__(
        self,
        db: Database,
        provider: Provider,
        settings: Settings,
        cache: Cache | None = None,
        name: str | None = None,
    ):
        self.db = db
        self.provider = provider
        self.settings = settings
        self.cache = cache
        self.name = name or f"{socket.gethostname()}-{os.getpid()}"
        self.concurrency = settings.worker_concurrency
        self.in_flight: set[asyncio.Task] = set()
        self.rate_limited = 0  # 429 answers in a row (they make the next wait longer)
        self.counts = {
            "claimed": 0,
            "succeeded": 0,
            "retried": 0,
            "failed": 0,
            "dead_letter": 0,
            "waiting": 0,
            "released": 0,
        }

    # ----- database steps (the pool is synchronous: they run in a thread) -----

    def _claim(self, n: int) -> list[dict]:
        with self.db.connection() as conn:
            jobs.expired_without_attempts(conn)
            return jobs.claim(conn, self.name, n, self.settings.job_lease_seconds)

    def _load(self, job: dict) -> tuple[dict | None, dict]:
        with self.db.connection() as conn:
            return repository.ticket_for_work(conn, job["ticket_id"]), repository.job_runs(
                conn, job["job_id"]
            )

    def _save_step(self, job: dict, ticket: dict, run: dict, extra: dict) -> None:
        with self.db.connection() as conn:  # one short transaction per step
            if not repository.save_job_ai_run(conn, ticket["ticket_id"], job["job_id"], run):
                return  # this job saved this step before (a second delivery): nothing to add
            if run["task"] == "classify":
                repository.set_classification(
                    conn, ticket["ticket_id"], extra["label"].team, extra["label"].priority
                )
            elif run["task"] == "embed":
                source = hashlib.sha256(f"{ticket['subject']}\n{ticket['body']}".encode())
                repository.save_embedding(
                    conn,
                    ticket["ticket_id"],
                    ai.EMBEDDING_VERSION,
                    extra["vector"],
                    source.hexdigest(),
                )

    def _finish(self, job: dict, state: str, error: str | None = None) -> bool:
        with self.db.connection() as conn:
            return jobs.finish(conn, job["job_id"], self.name, state, error)

    def _release(self, job: dict, delay: float = 0.0) -> bool:
        with self.db.connection() as conn:
            return jobs.release(conn, job["job_id"], self.name, delay)

    def _retry(self, job: dict, delay: float, error: str) -> bool:
        with self.db.connection() as conn:
            return jobs.retry_later(conn, job["job_id"], self.name, delay, error)

    # ----- the work -----

    async def do_steps(self, job: dict, ticket: dict, done: dict) -> None:
        s, b = ticket["subject"], ticket["body"]
        if "classify" not in done:
            answer, ms = await self.provider.acall("chat/completions", ai.classify_request(s, b))
            label = ai.parse_classification(answer)
            run = run_record(
                "classify",
                ai.CLASSIFY_PROMPT,
                answer,
                ms,
                f'{{"team": "{label.team}", "priority": {label.priority}}}',
            )
            await asyncio.to_thread(self._save_step, job, ticket, run, {"label": label})
        if "draft_reply" not in done:
            answer, ms = await self.provider.acall("chat/completions", ai.draft_request(s, b))
            run = run_record("draft_reply", ai.DRAFT_PROMPT, answer, ms, ai.parse_draft(answer))
            await asyncio.to_thread(self._save_step, job, ticket, run, {})
        if "embed" not in done:
            answer, ms, cached = await embed_cached(self.provider, self.cache, s, b)
            vector = ai.parse_embedding(answer)
            if cached:
                answer = {**answer, "usage": {"prompt_tokens": 0, "completion_tokens": 0}}
            output = f"vector {ai.EMBEDDING_VERSION}" + (" (from the cache)" if cached else "")
            run = run_record("embed", None, answer, ms, output)
            await asyncio.to_thread(self._save_step, job, ticket, run, {"vector": vector})

    async def process(self, job: dict) -> str:
        """Run one job; return the state it ends in (or 'lost' if another worker took it)."""
        try:
            ticket, done = await asyncio.to_thread(self._load, job)
            if ticket is None:
                state = "failed"
                await asyncio.to_thread(self._finish, job, state, "the ticket does not exist")
                return state
            await self.do_steps(job, ticket, done)
            ok = await asyncio.to_thread(self._finish, job, "succeeded")
            self.rate_limited = 0
            state = "succeeded" if ok else "lost"
        except asyncio.CancelledError:
            # The worker is stopping and the job did not finish in time: give it back.
            await asyncio.to_thread(self._release, job)
            self.counts["released"] += 1
            logger.info("job %s: given back to the queue (the worker is stopping)", job["job_id"])
            raise
        except BreakerOpen as error:
            state = "released"
            await asyncio.to_thread(self._release, job, error.retry_after)
        except (ai.BadAnswer, ProviderRejected) as error:
            state = "failed"
            await asyncio.to_thread(self._finish, job, state, f"{type(error).__name__}: {error}")
        except ProviderRateLimited as error:
            # Over the quota is not the job's fault: the job waits and keeps its attempts.
            # (Measured by the course: when these waits counted as attempts, a burst turned
            # 99 of 180 jobs into dead letters, because the quota counts over a whole minute.)
            state = "waiting"
            self.rate_limited += 1
            delay = max(
                error.retry_after or 0,
                jobs.backoff_seconds(
                    min(self.rate_limited, 6),
                    self.settings.retry_base_seconds,
                    self.settings.retry_cap_seconds,
                ),
            )
            await asyncio.to_thread(self._release, job, delay)
        except ProviderError as error:
            message = f"{type(error).__name__}: {error}"
            if job["attempts"] >= job["max_attempts"]:
                state = "dead_letter"
                await asyncio.to_thread(self._finish, job, state, message)
            else:
                state = "retried"
                delay = jobs.backoff_seconds(
                    job["attempts"],
                    self.settings.retry_base_seconds,
                    self.settings.retry_cap_seconds,
                )
                await asyncio.to_thread(self._retry, job, delay, message)
        if state in self.counts:
            self.counts[state] += 1
        logger.info("job %s: %s (attempt %s)", job["job_id"], state, job["attempts"])
        return state

    async def run_once(self) -> int:
        """Claim what fits into the free slots and start it. Returns the number of new jobs."""
        free = self.concurrency - len(self.in_flight)
        if free <= 0:
            return 0
        claimed = await asyncio.to_thread(self._claim, free)
        for job in claimed:
            task = asyncio.create_task(self.process(job))
            self.in_flight.add(task)
            task.add_done_callback(self.in_flight.discard)
        self.counts["claimed"] += len(claimed)
        return len(claimed)

    async def drain(self) -> None:
        """Run until no job is ready and none is in flight (for --once and the tests)."""
        while True:
            started = await self.run_once()
            if not self.in_flight and not started:
                return
            if self.in_flight:
                await asyncio.wait(self.in_flight, return_when=asyncio.FIRST_COMPLETED)

    async def run_forever(self, stop: asyncio.Event) -> None:
        stopping = asyncio.create_task(stop.wait())
        while not stop.is_set():
            started = await self.run_once()
            if started == 0 or len(self.in_flight) >= self.concurrency:
                await asyncio.wait(
                    {stopping} | self.in_flight,
                    timeout=self.settings.worker_poll_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
        await self.shutdown()

    async def shutdown(self) -> None:
        """Graceful shutdown: no new jobs; the running ones get WORKER_DRAIN_SECONDS to
        finish; the rest go back to the queue."""
        if not self.in_flight:
            return
        seconds = self.settings.worker_drain_seconds
        logger.info(
            "stopping: %d job(s) running, waiting up to %.0f s", len(self.in_flight), seconds
        )
        _, pending = await asyncio.wait(set(self.in_flight), timeout=seconds)
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)


def make_worker(settings: Settings, name: str | None = None, provider: Provider | None = None):
    db = Database(
        settings.database_url,
        min_size=1,
        max_size=max(2, settings.worker_concurrency + 1),
        timeout=settings.db_pool_timeout,
    )
    # No quick retries in the worker: a failed job goes back to the queue and waits there.
    provider = provider or make_provider(settings, retries=0)
    cache = make_cache(settings.cache_url, settings.cache_timeout)
    return Worker(db, provider, settings, cache, name)


async def main_async(args: argparse.Namespace) -> int:
    settings = load_settings()
    if args.concurrency:
        from dataclasses import replace

        settings = replace(settings, worker_concurrency=args.concurrency)
    worker = make_worker(settings, args.name)
    worker.db.open()
    started = time.perf_counter()
    print(
        f"Worker {worker.name}: up to {worker.concurrency} jobs at a time. "
        + ("Takes what is queued, then stops." if args.once else "Stop it with Ctrl+C.")
    )
    stop = asyncio.Event()

    def on_signal(*_) -> None:
        if not stop.is_set():
            print(
                f"Stopping: no new jobs; {len(worker.in_flight)} running job(s) get up to "
                f"{settings.worker_drain_seconds:.0f} s to finish.",
                flush=True,
            )
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, on_signal)
        except (NotImplementedError, AttributeError, ValueError):  # Windows
            signal.signal(sig, lambda *a: loop.call_soon_threadsafe(on_signal))
    try:
        if args.once:
            await worker.drain()
        else:
            await worker.run_forever(stop)
    finally:
        worker.db.close()
        await worker.provider.aclose()
        worker.provider.close()
        if worker.cache is not None:
            await worker.cache.close()
    c = worker.counts
    print(
        f"Done in {time.perf_counter() - started:.1f} s: {c['claimed']} taken, {c['succeeded']} "
        f"succeeded, {c['waiting']} waiting for the quota, {c['retried']} to retry later, "
        f"{c['failed']} failed, "
        f"{c['dead_letter']} dead letters, {c['released']} given back to the queue."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the worker that does the AI work of jobs.")
    parser.add_argument("--once", action="store_true", help="take what is queued, then stop")
    parser.add_argument(
        "--concurrency", type=int, help="jobs at the same time (WORKER_CONCURRENCY)"
    )
    parser.add_argument("--name", help="the worker's name in the jobs table")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        return asyncio.run(main_async(args))
    except SettingsError as error:
        print(f"Settings error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
