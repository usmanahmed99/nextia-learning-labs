-- AI work for every new ticket (the scaling course, Module 1).
-- New tickets come from the API now, so the database gives them their numbers:
-- T-500001, T-500002, ... (the loaded tickets stop below T-400001).
CREATE SEQUENCE ticket_number_seq START 500001;

-- The third AI task: an embedding of the ticket's text, made by the provider.
ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_task_known;
ALTER TABLE ai_runs ADD CONSTRAINT ai_runs_task_known
    CHECK (task IN ('classify', 'draft_reply', 'embed'));

-- The provider's embedding model makes vectors of 384 numbers too, but they cannot be
-- compared with e5-small's. So they get their own version, and it is not the current one.
INSERT INTO embedding_versions (version, model, revision, dimensions, is_current)
VALUES ('embed-small-384-v1', 'embed-small (text-embedding-3-small)', 'dimensions=384', 384, false);
