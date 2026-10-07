-- One row per ticket row in the export, with the customer's attributes.
-- LEFT JOIN keeps tickets with no customer (guests) and tickets whose
-- customer is no longer in the customer table. Duplicates are kept here:
-- the cleaning step removes them and counts them.
SELECT
    t.ticket_id,
    t.customer_id,
    t.created_at,
    t.channel,
    t.team,
    t.priority,
    t.order_value,
    t.word_count,
    t.first_reply_minutes,
    t.priority_now,
    t.closed_at,
    c.segment,
    c.region,
    c.joined_on
FROM tickets AS t
LEFT JOIN customers AS c
    ON c.customer_id = t.customer_id
WHERE t.created_at >= :created_from
  AND t.created_at <  :created_before
ORDER BY t.ticket_id;
