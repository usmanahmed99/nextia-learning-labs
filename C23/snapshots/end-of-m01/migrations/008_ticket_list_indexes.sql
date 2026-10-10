-- migrate: no-transaction
-- The indexes that the measured queries need (Module 4 of the databases course):
-- 1. the ticket list: one team's open tickets, newest first (status, team, then the
--    keyset columns, in the same order as ORDER BY);
-- 2. the latest AI run of a ticket (the list shows it);
-- 3. the messages of a ticket (the ticket page, and deleting a ticket).
-- CONCURRENTLY builds an index without blocking writes; it cannot run in a transaction.
CREATE INDEX CONCURRENTLY IF NOT EXISTS tickets_queue_idx
    ON tickets (status, team, created_at DESC, ticket_id DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ai_runs_ticket_idx
    ON ai_runs (ticket_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS messages_ticket_idx
    ON messages (ticket_id);
