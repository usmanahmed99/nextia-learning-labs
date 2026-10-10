# Ingestion sequence: a shop uploads a document

Journey J3. The upload returns at once; the slow work runs in the background, so a slow model never blocks an upload.

```mermaid
sequenceDiagram
    autonumber
    participant E as Editor (Ines)
    participant A as Assistant API
    participant F as File storage
    participant DB as PostgreSQL
    participant W as Ingestion worker
    participant M as Model provider
    E->>A: upload returns-policy.md (version 5)
    A->>F: save the file: tenant/bramble/returns-policy/v5
    A->>DB: one transaction: document version 5 (status "processing") + a job row
    A-->>E: 202 Accepted: job 812
    W->>DB: take the next job (SELECT ... FOR UPDATE SKIP LOCKED)
    W->>F: read the file
    W->>W: parse and chunk (about 0.1 ms for a Markdown file)
    W->>M: embed all chunks in one call (about 0.44 s for a long document)
    W->>M: summarize the document (chat-small, about 1.9 s)
    W->>DB: one transaction: chunks, vectors, summary; version 5 "active", version 4 "replaced"; job "succeeded"
    Note over W,DB: If the worker stops halfway, the job goes back to the queue and nothing is half-saved.
```
