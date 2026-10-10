"""The jobs of the queue: state, result, cancel, retry, and the queue's numbers (Module 4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.concurrency import run_in_threadpool

from ticket_api import jobs
from ticket_api.db import Database
from ticket_api.intake import get_db
from ticket_api.models import ErrorResponse, Job, JobResult, QueueStats
from ticket_api.security import require_api_key

router = APIRouter(prefix="/v1", tags=["jobs"], dependencies=[Depends(require_api_key)])
JobId = Annotated[int, Path(ge=1)]
NOT_FOUND = {404: {"model": ErrorResponse, "description": "No such job."}}


def read_job(db: Database, job_id: int) -> Job:
    with db.connection() as conn:
        job = jobs.get(conn, job_id)
        if job is None:
            raise HTTPException(404, f"Job {job_id} does not exist.")
        result = None
        if job["state"] == "succeeded":
            row = conn.execute(
                "SELECT t.team, t.priority,"
                " (SELECT output FROM ai_runs WHERE job_id = %(id)s AND task = 'draft_reply')"
                "   AS draft_reply,"
                " (SELECT embedding_version FROM ticket_embeddings e"
                "   WHERE e.ticket_id = t.ticket_id AND embedding_version = 'embed-small-384-v1')"
                "   AS embedding_version"
                " FROM tickets t WHERE t.ticket_id = %(ticket)s",
                {"id": job_id, "ticket": job["ticket_id"]},
            ).fetchone()
            result = JobResult(**row) if row else None
    return Job(**{k: job[k] for k in Job.model_fields if k in job}, result=result)


@router.get("/jobs/{job_id}", summary="Read a job: its state and result", responses=NOT_FOUND)
async def get_job(job_id: JobId, db: Annotated[Database, Depends(get_db)]) -> Job:
    return await run_in_threadpool(read_job, db, job_id)


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel a queued job",
    responses={409: {"model": ErrorResponse, "description": "The job is not queued."}, **NOT_FOUND},
)
async def cancel_job(job_id: JobId, db: Annotated[Database, Depends(get_db)]) -> Job:
    def cancel() -> None:
        with db.connection() as conn:
            job, changed = jobs.cancel(conn, job_id)
        if job is None:
            raise HTTPException(404, f"Job {job_id} does not exist.")
        if not changed:
            raise HTTPException(
                409, f"Job {job_id} is {job['state']}: only a queued job can be cancelled."
            )

    await run_in_threadpool(cancel)
    return await run_in_threadpool(read_job, db, job_id)


@router.post(
    "/jobs/{job_id}/retry",
    summary="Send a dead letter back to the queue",
    responses={
        409: {"model": ErrorResponse, "description": "The job is not a dead letter."},
        **NOT_FOUND,
    },
)
async def retry_job(job_id: JobId, db: Annotated[Database, Depends(get_db)]) -> Job:
    def retry() -> None:
        with db.connection() as conn:
            job, changed = jobs.requeue(conn, job_id)
        if job is None:
            raise HTTPException(404, f"Job {job_id} does not exist.")
        if not changed:
            raise HTTPException(409, f"Job {job_id} is {job['state']}, not a dead letter.")

    await run_in_threadpool(retry)
    return await run_in_threadpool(read_job, db, job_id)


@router.get("/queue", summary="The queue's numbers: waiting, running, oldest, finished")
async def queue_stats(request: Request, db: Annotated[Database, Depends(get_db)]) -> QueueStats:
    def read() -> dict:
        with db.connection() as conn:
            return jobs.stats(conn)

    return QueueStats(**await run_in_threadpool(read))
