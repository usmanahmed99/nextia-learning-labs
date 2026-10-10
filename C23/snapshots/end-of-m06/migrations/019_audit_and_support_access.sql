-- Audit events and time-limited support access (the authentication course, Module 5).
--
-- An audit event says who did (or tried) what, in which organization, and the result.
-- It never holds a token, a password, a cookie or a message's text.
CREATE TABLE audit_events (
    event_id   bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    at         timestamptz NOT NULL DEFAULT now(),
    actor_id   text,
    actor_kind text        NOT NULL,
    tenant_id  text,
    action     text        NOT NULL,
    target     text,
    result     text        NOT NULL,
    reason     text,
    request_id text,
    details    jsonb       NOT NULL DEFAULT '{}',
    CONSTRAINT audit_actor_kind_known CHECK (actor_kind IN ('user', 'service', 'system')),
    CONSTRAINT audit_result_known CHECK (result IN ('allowed', 'denied', 'done', 'failed'))
);
CREATE INDEX audit_events_tenant_idx ON audit_events (tenant_id, at DESC);
CREATE INDEX audit_events_actor_idx ON audit_events (actor_id, at DESC);

-- Append-only: an event cannot be changed or deleted, not even by the owner of the table
-- (a trigger runs for every role; only a person who can drop the trigger can get around it,
-- and that is a schema change that a migration would show).
CREATE FUNCTION audit_events_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit events cannot be changed or deleted';
END
$$;
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
REVOKE UPDATE, DELETE ON audit_events FROM ticket_app;  -- given by 017's default privileges

-- Support access: a platform administrator (not a member) may read ONE organization's
-- tickets for a short time, with a reason that the organization's owner can see.
CREATE TABLE support_grants (
    grant_id   uuid        PRIMARY KEY,
    tenant_id  text        NOT NULL REFERENCES tenants (tenant_id),
    user_id    text        NOT NULL REFERENCES users (user_id),
    reason     text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CONSTRAINT support_grants_reason_given CHECK (length(btrim(reason)) >= 10),
    CONSTRAINT support_grants_at_most_one_hour
        CHECK (expires_at > created_at AND expires_at <= created_at + interval '1 hour')
);
CREATE INDEX support_grants_active_idx ON support_grants (tenant_id, user_id, expires_at);

-- An organization that is being deleted, then deleted (its rows are gone; its audit stays).
ALTER TABLE tenants DROP CONSTRAINT tenants_status_known,
    ADD CONSTRAINT tenants_status_known CHECK (status IN ('active', 'deleting', 'deleted')),
    ADD COLUMN deleted_at timestamptz;
