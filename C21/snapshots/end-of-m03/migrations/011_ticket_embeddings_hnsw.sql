-- migrate: no-transaction
-- An approximate nearest-neighbour index (HNSW) for the current embedding version.
-- It is a partial index: it holds only the vectors of one version, and a query
-- uses it only when it asks for that version.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ticket_embeddings_e5_small_v1_hnsw
    ON ticket_embeddings USING hnsw (embedding vector_cosine_ops)
    WHERE embedding_version = 'e5-small-v1';
