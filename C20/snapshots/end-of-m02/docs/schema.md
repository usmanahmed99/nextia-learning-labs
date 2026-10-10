# The help desk's schema

The schema at the end of Module 2 (migrations 004 to 006). Later migrations change it: the cost
becomes `numeric` (007), files get an upload status (009), and vectors get a version (010).

```mermaid
erDiagram
    customers ||--o{ tickets : "writes"
    tickets ||--o{ messages : "has"
    tickets ||--o{ attachments : "has"
    tickets ||--o{ ai_runs : "is processed by"
    tickets ||--o{ ticket_embeddings : "is described by"
    documents {
        text doc_id PK
        int version PK
        text title
        date effective_from
        text body
        text sha256
    }
    customers {
        text customer_id PK "C-0001"
        text name
        text email "unique, any case"
        text segment
    }
    tickets {
        text ticket_id PK "T-30001"
        text customer_id FK
        text subject
        text body
        text team
        smallint priority "1 to 3"
        text status
        timestamptz created_at
        int message_count "a deliberate copy"
    }
    messages {
        bigint message_id PK
        text ticket_id FK
        text author "customer or agent"
        text body
    }
    attachments {
        uuid attachment_id PK
        text ticket_id FK
        text object_key "unique: where the file is"
        bigint size_bytes
        text sha256
    }
    ai_runs {
        bigint run_id PK
        text ticket_id FK "NULL after an erasure"
        text model
        text prompt_version
        int tokens_in
        int tokens_out
        real cost_usd
    }
    ticket_embeddings {
        text ticket_id PK
        vector embedding "384 numbers"
    }
```

One customer has zero or more tickets; one ticket has zero or more messages, attachments, AI
runs and vectors. Documents stand alone: the assistants read them, and no ticket owns them.

Identifiers are stable: a ticket keeps `T-30001` for its whole life, and no other ticket ever
gets that ID. Messages and AI runs get a number from the database.
