-- Deliberate denormalization: the ticket list shows how many messages a ticket
-- has and when the last one came. Counting them for every row of every list is
-- slow, so the ticket keeps both numbers. The cost: every new message must
-- update them in the same transaction (ticket_api/repository.py does).
ALTER TABLE tickets
    ADD COLUMN message_count integer NOT NULL DEFAULT 0,
    ADD COLUMN last_message_at timestamptz,
    ADD CONSTRAINT tickets_message_count_not_negative CHECK (message_count >= 0);

UPDATE tickets t
SET message_count = s.n, last_message_at = s.last_at
FROM (SELECT ticket_id, count(*) AS n, max(created_at) AS last_at
      FROM messages GROUP BY ticket_id) s
WHERE s.ticket_id = t.ticket_id;
