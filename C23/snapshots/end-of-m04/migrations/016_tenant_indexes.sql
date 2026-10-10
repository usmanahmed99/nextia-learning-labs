-- migrate: no-transaction
-- Every list query now starts with the organization (Module 4 of the authentication
-- course): WHERE tenant_id = ... AND status = ... AND team = ... ORDER BY created_at DESC.
-- The index starts with the organization too. Without it, a small organization's list
-- reads through the big organization's matching rows first (measured on the large data:
-- see the course's facts). The old queue index has the same columns without the
-- organization: it is replaced.
CREATE INDEX CONCURRENTLY IF NOT EXISTS tickets_tenant_queue_idx
    ON tickets (tenant_id, status, team, created_at DESC, ticket_id DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS tickets_tenant_created_idx
    ON tickets (tenant_id, created_at DESC, ticket_id DESC);
DROP INDEX CONCURRENTLY IF EXISTS tickets_queue_idx;
