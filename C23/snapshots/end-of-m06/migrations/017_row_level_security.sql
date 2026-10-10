-- Row-level security: a second lock behind the application's own tenant checks
-- (Module 4 of the authentication course).
--
-- Every query of the API already has "tenant_id = ..." in it. If one query forgets it,
-- these policies still let PostgreSQL return only the rows of the organization that the
-- API set for the transaction (app.tenant_id). Two facts decide whether it works:
--
-- 1. Policies do not apply to a superuser, and not to a table's owner unless the table
--    has FORCE ROW LEVEL SECURITY. In Docker Compose the API connects as "tickets", the
--    superuser that created everything: for that user these policies do nothing. So the
--    API switches to a normal role, ticket_app, at the start of each transaction (only
--    when DB_ROW_SECURITY=true): SET LOCAL ROLE ticket_app, then app.tenant_id.
-- 2. Without app.tenant_id, ticket_app sees no rows at all (the setting is empty).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ticket_app') THEN
        CREATE ROLE ticket_app NOLOGIN;
    END IF;
END
$$;
-- The role that may switch to ticket_app: the user the migration runs as.
GRANT ticket_app TO CURRENT_USER;
GRANT USAGE ON SCHEMA public TO ticket_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ticket_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ticket_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ticket_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ticket_app;

-- One policy per table that holds an organization's records: a row is visible, and may be
-- written, only when its tenant_id is the transaction's app.tenant_id.
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON customers
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tickets
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON messages
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE attachments ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON attachments
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE ai_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ai_runs
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE ticket_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ticket_embeddings
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
