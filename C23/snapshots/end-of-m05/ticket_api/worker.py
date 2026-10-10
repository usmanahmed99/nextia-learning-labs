"""The background worker: run queued jobs, each as the person who asked, in their organization
(the authentication course, Module 5).

For every job the worker reads the actor and the organization FROM THE JOB ROW (not from a
queue message), then asks the same question as the API: may this person, with their
membership as it is NOW, do this action in this organization? A person who was removed, or
whose role changed, since they asked gets the job refused. The work itself runs with the
organization in every query (and row-level security for that organization).
"""

import csv
import io
import logging

from psycopg.types.json import Jsonb

from ticket_api import audit, repository
from ticket_api.access import decide
from ticket_api.db import Database

logger = logging.getLogger("ticket_api")
ACTION = {"export": "export.create"}


def claim(db: Database) -> dict | None:
    """Take the oldest queued job (SKIP LOCKED: two workers never take the same job)."""
    with db.connection() as conn:
        return conn.execute(
            "UPDATE jobs SET status = 'running', started_at = now() WHERE job_id = ("
            " SELECT job_id FROM jobs WHERE status = 'queued' ORDER BY created_at"
            " FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *"
        ).fetchone()


def finish(
    db: Database, job: dict, status: str, reason: str | None = None, result: dict | None = None
) -> None:
    with db.connection() as conn:
        conn.execute(
            "UPDATE jobs SET status = %s, reason = %s, result = %s, finished_at = now()"
            " WHERE job_id = %s",
            (status, reason, Jsonb(result) if result is not None else None, job["job_id"]),
        )
        audit.write(
            conn,
            action=f"{job['kind']}.run",
            result="done" if status == "done" else "denied" if status == "refused" else "failed",
            actor_id=job["actor_id"],
            tenant_id=job["tenant_id"],
            target=str(job["job_id"]),
            reason=reason,
            details={"by": "worker", **(result or {})},
        )


def run_job(db: Database, job: dict, files=None, message: dict | None = None) -> str:
    """Run one claimed job. `message`: the queue message that named the job, if any. Its
    fields are only compared with the job row, never used."""
    if message and message.get("tenant_id") not in (None, job["tenant_id"]):
        finish(db, job, "refused", "the message names another organization than the job")
        return "refused"
    if job["kind"] == "tenant_delete":
        from ticket_api.lifecycle import purge_tenant

        try:
            result = purge_tenant(db, job["tenant_id"], files)
        except Exception as error:  # noqa: BLE001  (the job records why)
            finish(db, job, "failed", str(error)[:200])
            return "failed"
        finish(db, job, "done", result=result)
        return "done"
    with db.connection() as conn:
        role = repository.membership_role(conn, job["tenant_id"], job["actor_id"])
    decision = decide(role, ACTION[job["kind"]])
    if not decision.allowed:
        finish(db, job, "refused", f"{job['actor_id']}: {decision.rule} (checked when the job ran)")
        return "refused"
    params = job["params"] or {}
    with db.connection(job["tenant_id"]) as conn:
        rows = repository.export_rows(
            conn, tenant_id=job["tenant_id"], status=params.get("status"), team=params.get("team")
        )
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(
        ["ticket_id", "customer_id", "subject", "team", "priority", "status", "created_at"]
    )
    writer.writerows(
        [
            [
                r[k]
                for k in (
                    "ticket_id",
                    "customer_id",
                    "subject",
                    "team",
                    "priority",
                    "status",
                    "created_at",
                )
            ]
            for r in rows
        ]
    )
    result = {"rows": len(rows)}
    if files is not None:
        key = f"tenants/{job['tenant_id']}/exports/{job['job_id']}.csv"
        files.put(key, out.getvalue().encode(), "text/csv")
        result["object_key"] = key
    finish(db, job, "done", result=result)
    return "done"


def run_once(db: Database, files=None) -> list[tuple[str, str]]:
    """Run every queued job once. Returns (job ID, outcome) pairs."""
    done = []
    while (job := claim(db)) is not None:
        done.append((str(job["job_id"]), run_job(db, job, files)))
    return done
