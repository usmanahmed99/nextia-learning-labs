-- Deleting a customer's data everywhere (Module 5).
-- file_deletions is an outbox: the transaction that deletes the rows also writes
-- the keys of their files here. A separate step deletes the files and marks each
-- row done. If that step fails, the keys are still here, and it can run again.
CREATE TABLE file_deletions (
    object_key   text PRIMARY KEY,
    reason       text NOT NULL,
    requested_at timestamptz NOT NULL DEFAULT now(),
    deleted_at   timestamptz
);
CREATE INDEX file_deletions_pending_idx ON file_deletions (requested_at) WHERE deleted_at IS NULL;

-- A record that an erasure happened, with counts and no personal data.
CREATE TABLE erasures (
    erasure_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id text NOT NULL,
    erased_at   timestamptz NOT NULL DEFAULT now(),
    tickets     integer NOT NULL,
    messages    integer NOT NULL,
    files       integer NOT NULL,
    vectors     integer NOT NULL,
    ai_runs     integer NOT NULL
);

-- An erased customer's AI runs keep their cost, but lose their ticket and their text.
ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_ok_has_output;
ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_ok_has_output
    CHECK (status <> 'ok' OR output IS NOT NULL OR ticket_id IS NULL);

-- Erasing a customer deletes their tickets; for each deleted ticket, PostgreSQL checks
-- that no attachment row still points to it. Without an index on attachments
-- (ticket_id), each check reads the whole table: measured on the large data, the
-- business customer's 4,322 tickets took 7.7 s to erase, and 0.39 s with this index.
CREATE INDEX attachments_ticket_idx ON attachments (ticket_id);
