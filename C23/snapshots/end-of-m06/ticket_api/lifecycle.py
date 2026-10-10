"""Deleting an organization (the authentication course, Module 5).

Step 1, at once (the API): the organization's status becomes "deleting". From the next
request on, nobody gets in: every check joins the organization and needs "active".
Step 2, in the background (the worker): delete its rows in one transaction, put its files in
the outbox (file_deletions), then delete the files. The AI runs keep their cost with no
ticket and no text (as for a customer's erasure), the audit events stay, and the
organization's row stays with status "deleted", so its ID is never given to someone else.
"""

import psycopg

from ticket_api.db import Database


def purge_tenant(db: Database, tenant_id: str, files=None) -> dict:
    p = {"t": tenant_id}
    with db.connection() as conn:
        with conn.transaction():
            status = conn.execute(
                "SELECT status FROM tenants WHERE tenant_id = %(t)s FOR UPDATE", p
            ).fetchone()
            if status is None or status["status"] != "deleting":
                raise ValueError(f"{tenant_id} is not being deleted")
            count = lambda table: conn.execute(  # noqa: E731
                f"SELECT count(*) AS n FROM {table} WHERE tenant_id = %(t)s", p
            ).fetchone()["n"]
            counts = {
                t: count(t)
                for t in (
                    "customers",
                    "tickets",
                    "messages",
                    "attachments",
                    "ticket_embeddings",
                    "documents",
                    "memberships",
                )
            }
            conn.execute(
                "INSERT INTO file_deletions (object_key, reason)"
                " SELECT object_key, 'organization ' || %(t)s FROM attachments"
                " WHERE tenant_id = %(t)s"
                " ON CONFLICT (object_key) DO UPDATE SET deleted_at = NULL, requested_at = now()",
                p,
            )
            conn.execute("DELETE FROM attachments WHERE tenant_id = %(t)s", p)
            conn.execute(
                "UPDATE ai_runs SET output = NULL, ticket_id = NULL WHERE tenant_id = %(t)s", p
            )
            conn.execute("DELETE FROM tickets WHERE tenant_id = %(t)s", p)  # messages, vectors
            for table in ("customers", "documents", "invitations", "memberships", "support_grants"):
                conn.execute(f"DELETE FROM {table} WHERE tenant_id = %(t)s", p)
            conn.execute(
                "UPDATE jobs SET status = 'refused', reason = 'organization deleted',"
                " finished_at = now() WHERE tenant_id = %(t)s AND status = 'queued'",
                p,
            )
            conn.execute(
                "UPDATE tenants SET status = 'deleted', deleted_at = now() WHERE tenant_id = %(t)s",
                p,
            )
        files_deleted = 0
        if files is not None:
            from scripts.erase_customer import finish

            _, files_deleted = finish(conn, files)
            for key in list(files.keys(f"tenants/{tenant_id}/")):  # exports and new uploads
                files_deleted += bool(files.delete(key))
    return {**counts, "files_deleted": files_deleted}


def remaining(conn: psycopg.Connection, tenant_id: str) -> dict:
    """Rows of the organization that are still there (all 0 after a purge, but the AI runs)."""
    out = {}
    for table in (
        "customers",
        "tickets",
        "messages",
        "attachments",
        "ticket_embeddings",
        "documents",
        "memberships",
        "ai_runs",
    ):
        out[table] = conn.execute(
            f"SELECT count(*) AS n FROM {table} WHERE tenant_id = %s", (tenant_id,)
        ).fetchone()["n"]
    return out
