# Where each piece of data lives

The help desk's storage map: for each kind of data, the store that keeps the original
(the source of truth), the stores that keep a copy, and how a copy is made again.

| Data | Original in | Copies in | If a copy is lost |
|---|---|---|---|
| Customers | PostgreSQL `customers` | none | not a copy: restore it from a backup |
| Tickets and messages | PostgreSQL `tickets`, `messages` | ticket vectors (made from the text) | not a copy: restore it from a backup |
| Files that customers attach | object storage (Azurite on your computer), one object per file | none | not a copy: back up the object storage separately |
| File details (name, size, checksum, owner) | PostgreSQL `attachments` | none | restore it from a backup; check that every file still exists |
| Policy documents | PostgreSQL `documents` (each version) | none | restore it from a backup |
| AI runs (model, prompt version, tokens, cost) | PostgreSQL `ai_runs` | none | restore it from a backup |
| Ticket vectors | none: they are a copy | PostgreSQL `ticket_embeddings` (pgvector) | make them again from the ticket text with the same model and version: `python -m scripts.embed --rebuild` |
| Similar-ticket index (HNSW) | none: it is a copy | PostgreSQL index on `ticket_embeddings` | build it again: `REINDEX INDEX ...` or drop and create it |
| Cached answers (if you add a cache) | none: they are a copy | the cache | nothing to do: the next request fills it again |

Rules:

- Every copy says what it was made from: a vector has its ticket ID, its embedding version and a checksum of the text.
- A copy is never the only place where a fact is kept. If the vector store were lost, nothing a customer wrote would be lost.
