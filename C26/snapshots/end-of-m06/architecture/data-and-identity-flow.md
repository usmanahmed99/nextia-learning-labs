# Data and identity flow: where the tenant travels

Every request and every job carries the tenant. The database refuses a row of another tenant even when the code forgets a filter (row-level security, as in the authentication course).

```mermaid
flowchart LR
    U[Person signs in] -->|token: user, tenant, role| A[Assistant API]
    A -->|SET app.tenant for the transaction| DB[(PostgreSQL<br/>row-level security)]
    A -->|tenant in the cache key| C[(Answer cache<br/>in PostgreSQL)]
    A -->|tenant in the job row| Q[(Job queue<br/>in PostgreSQL)]
    Q --> W[Ingestion worker]
    W -->|SET app.tenant from the job| DB
    W -->|files under tenant/&lt;id&gt;/| F[(File storage)]
    A -->|only this tenant's passages| M[Model provider]
    DB -->|answer + document versions| L[Audit log]
```

| Data | Where | Tenant key | Version | Who may read it |
|---|---|---|---|---|
| Document file | File storage | folder `tenant/<id>/` | one file per version | the worker; staff of that tenant |
| Chunks and vectors | PostgreSQL | `tenant_id` + row-level security | `document_version` | the API for that tenant (public documents for customers) |
| Answer | PostgreSQL | `tenant_id` | the document versions it cited | staff and owner of that tenant |
| Cache entry | PostgreSQL | in the key | documents version in the key | the API for that tenant and audience |
| Job | PostgreSQL | `tenant_id` | the document version | the worker |

Measured: row-level security added about 0.1 ms to a request in the authentication course (4.3 ms off, 4.4 ms on).
