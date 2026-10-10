-- Vectors with a version (Module 5). A vector is only comparable with vectors of
-- the same model; the version says which model made it, and the checksum says
-- which text it was made from (so a changed ticket shows up as a stale vector).
CREATE TABLE embedding_versions (
    version    text PRIMARY KEY,
    model      text NOT NULL,
    revision   text NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions > 0),
    is_current boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
-- At most one current version.
CREATE UNIQUE INDEX embedding_versions_one_current ON embedding_versions (is_current) WHERE is_current;

-- The vectors that exist were all made by e5-small, revision 614241f.
INSERT INTO embedding_versions (version, model, revision, dimensions, is_current)
VALUES ('e5-small-v1', 'intfloat/multilingual-e5-small', '614241f622f53c4eeff9890bdc4f31cfecc418b3', 384, true);

ALTER TABLE ticket_embeddings
    ADD COLUMN embedding_version text NOT NULL DEFAULT 'e5-small-v1'
        REFERENCES embedding_versions (version),
    ADD COLUMN source_sha256 text,
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE ticket_embeddings ALTER COLUMN embedding_version DROP DEFAULT;

UPDATE ticket_embeddings e
SET source_sha256 = encode(sha256(convert_to(t.subject || E'\n' || t.body, 'UTF8')), 'hex')
FROM tickets t
WHERE t.ticket_id = e.ticket_id;
ALTER TABLE ticket_embeddings ALTER COLUMN source_sha256 SET NOT NULL;

-- One vector per ticket and version: the new key.
ALTER TABLE ticket_embeddings DROP CONSTRAINT ticket_embeddings_pkey;
ALTER TABLE ticket_embeddings ADD PRIMARY KEY (ticket_id, embedding_version);
