-- Every help-desk record now belongs to one organization (tenant_id).
--
-- 1. The column, filled with 'larkfield' for the rows that exist (a constant
--    default is fast: PostgreSQL does not rewrite the table), then no default:
--    from now on, every insert must say which organization the row is for.
-- 2. Keys and foreign keys that include the organization. A message, a file, a
--    vector or an AI run can only point to a ticket of the SAME organization,
--    and a ticket only to a customer of the same organization: the database
--    refuses a link across organizations, whatever the application does.
-- 3. Rules that were global become per organization: two shops can have a
--    customer with the same email address, and a document with the same name.
ALTER TABLE customers ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield' REFERENCES tenants (tenant_id);
ALTER TABLE tickets ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield' REFERENCES tenants (tenant_id);
ALTER TABLE messages ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield';
ALTER TABLE orphaned_messages ADD COLUMN tenant_id text;
ALTER TABLE attachments ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield';
ALTER TABLE ai_runs ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield' REFERENCES tenants (tenant_id);
ALTER TABLE ticket_embeddings ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield';
ALTER TABLE documents ADD COLUMN tenant_id text NOT NULL DEFAULT 'larkfield' REFERENCES tenants (tenant_id);

ALTER TABLE customers ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE tickets ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE messages ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE attachments ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE ai_runs ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE ticket_embeddings ALTER COLUMN tenant_id DROP DEFAULT;
ALTER TABLE documents ALTER COLUMN tenant_id DROP DEFAULT;

-- The IDs stay unique across all organizations (a ticket ID names one ticket),
-- and the pair (tenant_id, id) is what the foreign keys use.
ALTER TABLE customers ADD CONSTRAINT customers_tenant_key UNIQUE (tenant_id, customer_id);
ALTER TABLE tickets ADD CONSTRAINT tickets_tenant_key UNIQUE (tenant_id, ticket_id);

ALTER TABLE tickets DROP CONSTRAINT tickets_customer_fk,
    ADD CONSTRAINT tickets_customer_fk FOREIGN KEY (tenant_id, customer_id)
        REFERENCES customers (tenant_id, customer_id);
ALTER TABLE messages DROP CONSTRAINT messages_ticket_fk,
    ADD CONSTRAINT messages_ticket_fk FOREIGN KEY (tenant_id, ticket_id)
        REFERENCES tickets (tenant_id, ticket_id) ON DELETE CASCADE;
ALTER TABLE attachments DROP CONSTRAINT attachments_ticket_fk,
    ADD CONSTRAINT attachments_ticket_fk FOREIGN KEY (tenant_id, ticket_id)
        REFERENCES tickets (tenant_id, ticket_id);
-- An AI run keeps its organization (and its cost) when its ticket is deleted:
-- only ticket_id becomes NULL.
ALTER TABLE ai_runs DROP CONSTRAINT ai_runs_ticket_fk,
    ADD CONSTRAINT ai_runs_ticket_fk FOREIGN KEY (tenant_id, ticket_id)
        REFERENCES tickets (tenant_id, ticket_id) ON DELETE SET NULL (ticket_id);
ALTER TABLE ticket_embeddings DROP CONSTRAINT ticket_embeddings_ticket_fk,
    ADD CONSTRAINT ticket_embeddings_ticket_fk FOREIGN KEY (tenant_id, ticket_id)
        REFERENCES tickets (tenant_id, ticket_id) ON DELETE CASCADE;

-- Customer IDs: Larkfield's start with C-, Bramble Books' with B-.
ALTER TABLE customers DROP CONSTRAINT customers_id_format,
    ADD CONSTRAINT customers_id_format CHECK (customer_id ~ '^[A-Z]-[0-9]{4,5}$');
-- One account per email address IN EACH organization (Olga Olsen shops at both).
DROP INDEX customers_email_unique;
CREATE UNIQUE INDEX customers_email_unique ON customers (tenant_id, lower(email));
-- Each organization has its own documents: both shops can have a "returns-policy".
ALTER TABLE documents DROP CONSTRAINT documents_pkey, ADD PRIMARY KEY (tenant_id, doc_id, version);

