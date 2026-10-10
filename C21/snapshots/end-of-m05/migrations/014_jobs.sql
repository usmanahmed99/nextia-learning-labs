-- A job queue in PostgreSQL (the scaling course, Module 4).
-- A new ticket and its job are saved in the same transaction: there is never a ticket
-- without its job, or a job without its ticket (the "transactional outbox" advantage of a
-- queue in the same database). A worker process takes queued jobs with
-- SELECT ... FOR UPDATE SKIP LOCKED, so two workers never take the same job at once.
CREATE TABLE jobs (
    job_id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind            text        NOT NULL DEFAULT 'ticket_ai',
    ticket_id       text        NOT NULL REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    -- Who asked for the work (the job's identity). The worker trusts this row, never a
    -- message from outside.
    actor           text        NOT NULL,
    -- The caller's Idempotency-Key header: the same key again means the same request.
    idempotency_key text,
    request_sha256  text,
    state           text        NOT NULL DEFAULT 'queued',
    attempts        integer     NOT NULL DEFAULT 0,
    max_attempts    integer     NOT NULL DEFAULT 5,
    run_after       timestamptz NOT NULL DEFAULT now(),
    locked_by       text,
    locked_until    timestamptz,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    started_at      timestamptz,
    finished_at     timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT jobs_kind_known CHECK (kind IN ('ticket_ai')),
    CONSTRAINT jobs_state_known CHECK (state IN
        ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'dead_letter')),
    CONSTRAINT jobs_attempts_in_range CHECK (attempts >= 0 AND attempts <= max_attempts),
    CONSTRAINT jobs_finished_has_time
        CHECK ((state IN ('succeeded', 'failed', 'cancelled', 'dead_letter')) = (finished_at IS NOT NULL))
);
-- One job per caller and idempotency key.
CREATE UNIQUE INDEX jobs_idempotency_key ON jobs (actor, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
-- What the workers look for: queued jobs that may run now, and running jobs whose lease ended.
CREATE INDEX jobs_queued_idx ON jobs (run_after, job_id) WHERE state = 'queued';
CREATE INDEX jobs_running_idx ON jobs (locked_until) WHERE state = 'running';
CREATE INDEX jobs_ticket_idx ON jobs (ticket_id);
CREATE INDEX jobs_finished_idx ON jobs (finished_at) WHERE finished_at IS NOT NULL;

-- Each AI result says which job made it, and a job makes each task's result once: when a
-- job is delivered twice, the second delivery finds the result and does not add another.
ALTER TABLE ai_runs ADD COLUMN job_id bigint REFERENCES jobs (job_id) ON DELETE SET NULL;
CREATE UNIQUE INDEX ai_runs_one_per_job_task ON ai_runs (job_id, task) WHERE job_id IS NOT NULL;
