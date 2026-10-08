import json
import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response
from pydantic import BaseModel, Field

from escalation.contract import TicketIn
from escalation.errors import ErrorResponse, error_response
from escalation.jobs import QueueFull
from escalation.scoring import score_tickets
from escalation.security import require_api_key

predictions = logging.getLogger("escalation.predictions")

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])

ERRORS = {
    401: {"model": ErrorResponse, "description": "The API key is missing or wrong."},
    422: {"model": ErrorResponse, "description": "The ticket does not match the contract."},
}


class ScoreOut(BaseModel):
    ticket_id: str
    score: float = Field(ge=0, le=1, description="0 to 1. Higher means a higher risk of escalation.")
    flag: bool = Field(description="True: send the ticket to the senior team.")
    threshold: float = Field(description="The score at and above which a ticket is flagged.")
    model_version: str
    warnings: list[str] = Field(description="Values the model never saw. The score is less certain.")


class ModelInfo(BaseModel):
    model_version: str
    bundle_sha256: str
    threshold: float
    trained_at: str
    features: list[str]


class JobIn(BaseModel):
    tickets: list[TicketIn] = Field(min_length=1)


class JobStatus(BaseModel):
    job_id: str
    status: str = Field(description="queued, running, done or failed")
    tickets: int
    created_at: str
    finished_at: str | None = None
    seconds: float | None = None
    model_version: str | None = None
    results: list[dict] | None = None
    error: str | None = None


@router.post("/score", tags=["scoring"], summary="Score one new ticket", responses=ERRORS)
def score(ticket: TicketIn, request: Request, response: Response) -> ScoreOut:
    state = request.app.state
    [result], timings = score_tickets(state.bundle, [ticket])
    response.headers["Server-Timing"] = timings.header()
    record = {
        "request_id": request.state.request_id,
        "ticket_id": ticket.ticket_id,
        "model_version": state.bundle.version,
        "score": result.score,
        "flag": result.flag,
    }
    predictions.info(json.dumps(record))
    return ScoreOut(
        ticket_id=ticket.ticket_id,
        score=result.score,
        flag=result.flag,
        threshold=state.bundle.threshold,
        model_version=state.bundle.version,
        warnings=result.warnings,
    )


@router.get("/model", tags=["model"], summary="Which model answers, and how to check it")
def model(request: Request) -> ModelInfo:
    bundle = request.app.state.bundle
    return ModelInfo(
        model_version=bundle.version,
        bundle_sha256=bundle.digest,
        threshold=bundle.threshold,
        trained_at=bundle.metadata["trained_at"],
        features=bundle.contract["features"],
    )


def status_of(job) -> JobStatus:
    return JobStatus(
        job_id=job.id,
        status=job.status,
        tickets=len(job.results) if job.results is not None else len(job.tickets),
        created_at=job.created_at,
        finished_at=job.finished_at,
        seconds=job.seconds,
        model_version=job.model_version,
        results=job.results if job.status == "done" else None,
        error=job.error,
    )


@router.post(
    "/jobs",
    tags=["jobs"],
    status_code=202,
    summary="Score many tickets later",
    responses={**ERRORS, 429: {"model": ErrorResponse, "description": "Too many jobs are waiting."}},
)
def submit_job(job_in: Annotated[JobIn, Body()], request: Request, response: Response) -> JobStatus:
    limit = request.app.state.settings.max_job_tickets
    if len(job_in.tickets) > limit:
        return error_response(request, 413, "job_too_large", f"A job can have at most {limit} tickets.")
    try:
        job = request.app.state.jobs.submit(job_in.tickets)
    except QueueFull:
        return error_response(request, 429, "too_many_jobs", "Too many jobs are waiting. Try again later.")
    response.headers["Location"] = f"/v1/jobs/{job.id}"
    response.headers["Retry-After"] = "2"
    return status_of(job)


@router.get("/jobs/{job_id}", tags=["jobs"], summary="The status of a job, and its scores when done")
def get_job(job_id: str, request: Request) -> JobStatus:
    job = request.app.state.jobs.jobs.get(job_id)
    if job is None:
        return error_response(request, 404, "job_not_found", "There is no job with this ID here.")
    return status_of(job)
