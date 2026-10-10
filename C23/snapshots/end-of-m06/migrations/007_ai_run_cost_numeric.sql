-- Money is not a floating-point number. The old tool stored the cost of each AI
-- run as real (about 7 significant digits, in binary), so sums drift and some
-- values cannot be stored exactly. numeric(12, 8) stores the dollars exactly.
-- This rewrites the whole table and blocks it while it runs: time it on the
-- large data before you run it on a busy database.
ALTER TABLE ai_runs ALTER COLUMN cost_usd TYPE numeric(12, 8);
