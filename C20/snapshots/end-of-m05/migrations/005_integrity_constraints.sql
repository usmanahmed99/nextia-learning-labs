-- Rules that the database enforces for every program that writes to it.

-- 1. Three messages belong to tickets that do not exist (test tickets that were
--    deleted by hand in the old tool). A foreign key cannot be added while they
--    are there. Keep them in a separate table for a person to check, and remove
--    them from messages.
CREATE TABLE orphaned_messages (LIKE messages);
INSERT INTO orphaned_messages
SELECT m.* FROM messages m
WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.ticket_id = m.ticket_id);
DELETE FROM messages m
WHERE NOT EXISTS (SELECT 1 FROM tickets t WHERE t.ticket_id = m.ticket_id);

-- 2. Customers: required fields, one account per email address, known values.
ALTER TABLE customers
    ALTER COLUMN name SET NOT NULL,
    ALTER COLUMN email SET NOT NULL,
    ALTER COLUMN segment SET NOT NULL,
    ALTER COLUMN joined_on SET NOT NULL,
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ADD CONSTRAINT customers_id_format CHECK (customer_id ~ '^C-[0-9]{4,5}$'),
    ADD CONSTRAINT customers_segment_known CHECK (segment IN ('home', 'trade', 'business')),
    ADD CONSTRAINT customers_region_known CHECK (region IN ('north', 'south', 'east', 'west'));
-- "Ana@Example.com" and "ana@example.com" are the same address.
CREATE UNIQUE INDEX customers_email_unique ON customers (lower(email));

-- 3. Tickets: every ticket has a customer that exists, and known values.
ALTER TABLE tickets
    ALTER COLUMN customer_id SET NOT NULL,
    ALTER COLUMN subject SET NOT NULL,
    ALTER COLUMN body SET NOT NULL,
    ALTER COLUMN channel SET NOT NULL,
    ALTER COLUMN team SET NOT NULL,
    ALTER COLUMN priority SET NOT NULL,
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN status SET DEFAULT 'open',
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ADD CONSTRAINT tickets_id_format CHECK (ticket_id ~ '^T-[0-9]{5,6}$'),
    ADD CONSTRAINT tickets_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    ADD CONSTRAINT tickets_channel_known CHECK (channel IN ('email', 'web_form', 'chat', 'phone')),
    ADD CONSTRAINT tickets_team_known CHECK (team IN ('billing', 'login', 'shipping', 'account', 'other')),
    ADD CONSTRAINT tickets_priority_range CHECK (priority BETWEEN 1 AND 3),
    ADD CONSTRAINT tickets_status_known CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
    ADD CONSTRAINT tickets_subject_not_blank CHECK (btrim(subject) <> ''),
    -- A ticket has a closing time exactly when it is resolved or closed.
    ADD CONSTRAINT tickets_closed_at_matches_status
        CHECK ((status IN ('resolved', 'closed')) = (closed_at IS NOT NULL)),
    ADD CONSTRAINT tickets_times_in_order
        CHECK (updated_at >= created_at AND (closed_at IS NULL OR closed_at >= created_at));

-- 4. Messages belong to a ticket; deleting a ticket deletes its messages.
ALTER TABLE messages
    ALTER COLUMN ticket_id SET NOT NULL,
    ALTER COLUMN author SET NOT NULL,
    ALTER COLUMN body SET NOT NULL,
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ADD CONSTRAINT messages_ticket_fk FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE,
    ADD CONSTRAINT messages_author_known CHECK (author IN ('customer', 'agent')),
    ADD CONSTRAINT messages_body_not_blank CHECK (btrim(body) <> '');

-- 5. Attachments: the database cannot delete a file in object storage, so it
--    refuses to delete a ticket that still has attachments (no CASCADE here).
ALTER TABLE attachments
    ALTER COLUMN ticket_id SET NOT NULL,
    ALTER COLUMN file_name SET NOT NULL,
    ALTER COLUMN content_type SET NOT NULL,
    ALTER COLUMN size_bytes SET NOT NULL,
    ALTER COLUMN sha256 SET NOT NULL,
    ALTER COLUMN object_key SET NOT NULL,
    ALTER COLUMN uploaded_at SET NOT NULL,
    ADD CONSTRAINT attachments_ticket_fk FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id),
    ADD CONSTRAINT attachments_object_key_unique UNIQUE (object_key),
    ADD CONSTRAINT attachments_size_positive CHECK (size_bytes > 0),
    ADD CONSTRAINT attachments_sha256_format CHECK (sha256 ~ '^[0-9a-f]{64}$');

-- 6. Documents: a title, a body and its checksum for every version.
ALTER TABLE documents
    ALTER COLUMN title SET NOT NULL,
    ALTER COLUMN body SET NOT NULL,
    ALTER COLUMN sha256 SET NOT NULL,
    ALTER COLUMN effective_from SET NOT NULL,
    ADD CONSTRAINT documents_version_positive CHECK (version >= 1),
    ADD CONSTRAINT documents_dates_in_order CHECK (effective_to IS NULL OR effective_to >= effective_from);

-- 7. AI runs: numbers that cannot be negative, known values. The cost records
--    stay when a ticket is deleted (ticket_id becomes NULL), so that the
--    monthly cost stays right.
ALTER TABLE ai_runs
    ALTER COLUMN task SET NOT NULL,
    ALTER COLUMN model SET NOT NULL,
    ALTER COLUMN tokens_in SET NOT NULL,
    ALTER COLUMN tokens_out SET NOT NULL,
    ALTER COLUMN cost_usd SET NOT NULL,
    ALTER COLUMN latency_ms SET NOT NULL,
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ADD CONSTRAINT ai_runs_ticket_fk FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE SET NULL,
    ADD CONSTRAINT ai_runs_task_known CHECK (task IN ('classify', 'draft_reply')),
    ADD CONSTRAINT ai_runs_status_known CHECK (status IN ('ok', 'error', 'timeout')),
    ADD CONSTRAINT ai_runs_counts_not_negative
        CHECK (tokens_in >= 0 AND tokens_out >= 0 AND cost_usd >= 0 AND latency_ms >= 0),
    ADD CONSTRAINT ai_runs_ok_has_output CHECK (status <> 'ok' OR output IS NOT NULL);

-- 8. A vector belongs to a ticket; deleting the ticket deletes its vector.
ALTER TABLE ticket_embeddings
    ALTER COLUMN embedding SET NOT NULL,
    ADD CONSTRAINT ticket_embeddings_ticket_fk
        FOREIGN KEY (ticket_id) REFERENCES tickets (ticket_id) ON DELETE CASCADE;
