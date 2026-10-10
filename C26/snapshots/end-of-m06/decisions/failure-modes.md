# Failure modes

A tabletop review: for each failure, what users see, how we notice, what limits the damage, who acts. RTO and RPO targets: requirements.md Q7.

| ID | Failure | What users see | Detection signal | Mitigation | Owner | Recovery |
|---|---|---|---|---|---|---|
| F1 | Model provider outage or 429 (quota) | answers fail or wait | share of 5xx/429 from the provider over 5 minutes > 5% | timeout 10 s; circuit breaker (the scaling course measured 8 calls instead of 150 during a 20 s outage); a clear "try again in a minute" message; ingestion jobs wait in the queue | Amira | automatic when the provider is back; no data lost |
| F2 | Slow database | every answer is slow | p95 of the search query > 100 ms; connection pool waits | connection pool with a timeout; the indexes from the databases course; one bigger server size is a setting (ADR-0004) | Mei | minutes (resize) |
| F3 | Queue backlog | new documents are not searchable for hours | age of the oldest queued job > 15 minutes | the worker scales on queue age; the upload answer says "processing"; a bound on jobs per tenant | Mei | the backlog drains; no data lost |
| F4 | Partial ingestion (worker stops halfway) | an old version stays active, or a document is missing | jobs "running" past their lease; versions "processing" for more than 1 hour | one transaction for chunks, vectors and the version switch; the lease returns the job to the queue | Mei | automatic on the next delivery |
| F5 | Permission mistake (a tenant sees another tenant's data) | a wrong, private answer | cross-tenant checks in the evaluation set and the access tests; an audit query | row-level security in the database, the tenant in every cache key and job; the release stops when an access test fails | Kwame | contain at once, tell the tenant, find every affected answer in the audit log |
| F6 | Database lost or corrupted | the assistant is down | availability alert | point-in-time restore (ADR-0005), quarterly restore test | Mei | RTO about 70 minutes (estimate: people and a new server), RPO minutes |

## Single point of failure

The database is a single point of failure: every answer and every job needs it. The proportionate mitigation at this size is a tested restore (F6), not a second server. The provider's documentation says high availability needs a General Purpose server (not the Burstable B1ms) and bills a standby server of the same size: two D2ds_v5 servers cost about US$288 a month of compute (price list: US$0.1976 an hour each) instead of US$13.50, for an availability target (Q2) that the restore plan already meets. Revisit when Q2 rises above 99.9%.
