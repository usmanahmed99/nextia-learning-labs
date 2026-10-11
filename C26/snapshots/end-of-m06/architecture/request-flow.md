# Request flow: an agent asks a question

The primary flow (journey J1). Times are medians from the course team's runs (measured.toml); a real deployment adds network time.

```mermaid
sequenceDiagram
    autonumber
    participant T as Help-desk tool
    participant A as Assistant API
    participant DB as PostgreSQL
    participant M as Model provider
    T->>A: POST /v1/answers (question, token)
    A->>A: check the token: tenant, user, role
    A->>DB: set the tenant for this transaction (row-level security)
    A->>DB: answer cache: same tenant, same documents version, same question?
    alt cache hit (about 0.014 s)
        DB-->>A: the saved answer
    else cache miss
        A->>M: embed the question (embed-small, about 0.34 s)
        M-->>A: 384 numbers
        A->>DB: search this tenant's chunks (vector + keyword), rerank (about 0.32 s)
        DB-->>A: 5 passages with their document versions
        A->>M: answer with citations (chat-small, about 1.5 s)
        M-->>A: answer, claims, cited passage IDs
        A->>A: check the citations (IDs in the passages, numbers in the cited text)
        A->>DB: save the answer: question, citations, versions, tenant, user
    end
    A-->>T: 200: answer with citations
```

What can go wrong at each step is in `../decisions/failure-modes.md`.
