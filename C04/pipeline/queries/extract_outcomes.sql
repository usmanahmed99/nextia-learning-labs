-- Every outcome event of the tickets in the selection. Events for tickets
-- that are not in the ticket table are left out by the join.
SELECT
    o.outcome_id,
    o.ticket_id,
    o.recorded_at,
    o.status,
    o.resolution_code,
    o.csat
FROM outcomes AS o
WHERE o.ticket_id IN (
    SELECT t.ticket_id
    FROM tickets AS t
    WHERE t.created_at >= :created_from
      AND t.created_at <  :created_before
)
ORDER BY o.outcome_id;
