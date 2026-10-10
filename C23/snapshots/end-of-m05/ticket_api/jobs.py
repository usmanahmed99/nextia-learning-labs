"""Background exports: a person asks, a worker does the work later (the authentication course,
Module 5).

POST /v1/tenants/{tenant}/exports              owner, staff: queue an export of the tickets
GET  /v1/tenants/{tenant}/exports/{job_id}     its status, and a download link when it is done

The job row keeps WHO asked (actor_id) and for WHICH organization (tenant_id), from the
checked request: never from the request body. The worker (ticket_api/worker.py) checks both
again when it runs the job.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ticket_api import audit, repository
from ticket_api.deps import DB
from ticket_api.models import ErrorResponse, ExportIn, Job
from ticket_api.tenancy import Caller, require

router = APIRouter(prefix="/v1/tenants/{tenant}/exports", tags=["exports"])
ERRORS = {
    403: {"model": ErrorResponse, "description": "The role may not export."},
    404: {"model": ErrorResponse, "description": "No such organization, membership or job."},
}


@router.post(
    "", status_code=202, summary="Export the tickets (later, in the background)", responses=ERRORS
)
def start_export(
    body: ExportIn,
    caller: Annotated[Caller, Depends(require("export.create"))],
    db: DB,
    request: Request,
) -> Job:
    with db.connection(caller.tenant_id) as conn:
        job = repository.create_job(
            conn,
            str(uuid.uuid4()),
            caller.user_id,
            "export",
            body.model_dump(),
            tenant_id=caller.tenant_id,
        )
        audit.write(
            conn,
            action="export.queued",
            result="done",
            actor_id=caller.user_id,
            tenant_id=caller.tenant_id,
            target=str(job["job_id"]),
            request_id=request.state.request_id,
            details=body.model_dump(),
        )
    return Job(**job)


@router.get("/{job_id}", summary="The status of an export", responses=ERRORS)
def export_status(
    job_id: uuid.UUID,
    caller: Annotated[Caller, Depends(require("export.create"))],
    db: DB,
    request: Request,
) -> Job:
    with db.connection(caller.tenant_id) as conn:
        job = repository.get_job(conn, str(job_id), tenant_id=caller.tenant_id)
    if job["actor_id"] != caller.user_id and caller.role != "owner":
        raise repository.NotFound(f"Job {job_id} does not exist.")  # another member's export
    url = None
    store = request.app.state.files
    if job["status"] == "done" and store is not None and (job["result"] or {}).get("object_key"):
        url, _ = store.download_url(job["result"]["object_key"], 300, f"export-{job_id}.csv")
    return Job(**job, download_url=url)
