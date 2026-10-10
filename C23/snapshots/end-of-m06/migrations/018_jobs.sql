-- Background jobs that act for a person in an organization (the authentication course,
-- Module 5). The job row is the only source of who asked and for which organization:
-- a queue message carries the job's ID, nothing that the worker would trust. When the
-- job runs, the worker checks the actor's membership and role AGAIN: the person may have
-- been removed, or their role changed, since they asked.
CREATE TABLE jobs (
    job_id      uuid        PRIMARY KEY,
    tenant_id   text        NOT NULL REFERENCES tenants (tenant_id),
    actor_id    text        NOT NULL REFERENCES users (user_id),
    kind        text        NOT NULL,
    params      jsonb       NOT NULL DEFAULT '{}',
    status      text        NOT NULL DEFAULT 'queued',
    result      jsonb,
    reason      text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    started_at  timestamptz,
    finished_at timestamptz,
    CONSTRAINT jobs_kind_known CHECK (kind IN ('export', 'tenant_delete')),
    CONSTRAINT jobs_status_known
        CHECK (status IN ('queued', 'running', 'done', 'refused', 'failed'))
);
CREATE INDEX jobs_queued_idx ON jobs (created_at) WHERE status = 'queued';
CREATE INDEX jobs_tenant_idx ON jobs (tenant_id, created_at DESC);
-- The second lock of Module 4 for jobs too.
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON jobs
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
