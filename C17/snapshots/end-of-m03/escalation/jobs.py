"""Asynchronous scoring: accept a large job now, score it later, keep the result.

    POST /v1/jobs            202 Accepted, with the job's ID and status URL
    GET  /v1/jobs/{job_id}   queued → running → done (or failed), and the scores

One worker thread takes jobs from a queue, one at a time. The queue has a
limit: when it is full, a new job gets 429, so a burst cannot use all memory.

The jobs live in this process's memory. That is enough to learn the pattern,
but a restart loses every job, and a second worker process cannot see them.
A real service keeps jobs in a queue service and results in storage (C21).
"""

import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from escalation.contract import TicketIn
from escalation.scoring import score_tickets

logger = logging.getLogger("escalation")


class QueueFull(Exception):
    pass


@dataclass
class Job:
    id: str
    tickets: list[TicketIn]
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    finished_at: str | None = None
    seconds: float | None = None
    model_version: str | None = None
    results: list[dict] | None = None
    error: str | None = None


class JobRunner:
    def __init__(self, get_bundle, max_queued: int, extra_ms_per_ticket: float = 0.0):
        self.get_bundle = get_bundle
        self.extra_ms = extra_ms_per_ticket
        self.queue: queue.Queue[Job] = queue.Queue(maxsize=max_queued)
        self.jobs: dict[str, Job] = {}
        self.thread = threading.Thread(target=self.work, daemon=True, name="job-worker")
        self.thread.start()

    def submit(self, tickets: list[TicketIn]) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], tickets=tickets)
        try:
            self.queue.put_nowait(job)
        except queue.Full:
            raise QueueFull from None
        self.jobs[job.id] = job
        return job

    def work(self) -> None:
        while True:
            job = self.queue.get()
            job.status = "running"
            started = time.perf_counter()
            try:
                bundle = self.get_bundle()
                results, _ = score_tickets(bundle, job.tickets)
                if self.extra_ms:  # a stand-in for a slow model, such as a large text model
                    time.sleep(self.extra_ms * len(job.tickets) / 1000)
                job.results = [
                    {"ticket_id": t.ticket_id, "score": r.score, "flag": r.flag}
                    for t, r in zip(job.tickets, results)
                ]
                job.model_version = bundle.version
                job.status = "done"
            except Exception as error:  # a failed job must not stop the worker
                logger.exception("job %s failed", job.id)
                job.status, job.error = "failed", str(error)
            job.seconds = round(time.perf_counter() - started, 3)
            job.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            job.tickets = []  # the input is not needed any more
            self.queue.task_done()
