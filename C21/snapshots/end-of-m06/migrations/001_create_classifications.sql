-- The table that C18 made at start-up. IF NOT EXISTS: a database from C18
-- already has it, and this migration then only records that it is there.
CREATE TABLE IF NOT EXISTS classifications (
    id            bigserial PRIMARY KEY,
    request_id    text        NOT NULL,
    category      text        NOT NULL,
    priority      smallint    NOT NULL,
    confidence    real        NOT NULL,
    model_version text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);
