# ADR-0002: PostgreSQL for records, vectors, the job queue and the answer cache

## Status

Accepted. Mei and Kwame.

## Context

Tomás asked for a vector database service and a separate cache. The whole base workload stores about 18 MB in month 0 and grows about 16 MB a month (cost model: measured bytes per chunk, vector and answer). The databases course measured an HNSW search over 10,000 vectors in about 0.2 ms; the scaling course measured a PostgreSQL job queue at about 2,600 jobs a second, while we need fewer than 50 ingestion jobs a month.

## Options

1. PostgreSQL with pgvector for everything: one store to back up, one place for row-level security.
2. PostgreSQL + a vector database service: a second bill, a second copy of every tenant's data, tenant isolation in two places.
3. PostgreSQL + Valkey for the cache: faster cache lookups, a second service to run.

## Decision

Option 1. The answer cache is a table with the tenant and the documents version in its key.

## Consequences

- One backup and one restore test cover all the data (Q7).
- A cache hit costs a database query, not a memory lookup; at our size that is a few milliseconds.

## Revisit when

- Vector search p95 passes 100 ms, or the chunks pass 5 million rows, or
- the cache table causes measurable load on the database (more than 20% of its CPU).
