# What the ticket API caches, for whom and for how long

The worked example of the scaling course, Module 3. One row per result that the API makes. "Scope" is who may receive a cached copy; it is part of the key.

| Result | Depends on | Cache it? | Scope in the key | TTL | Made old by (invalidation) |
|---|---|---|---|---|---|
| The list of ticket categories | nothing (fixed in the code) | no need: it costs nothing to make | everyone | - | a new release |
| A document's text | the document's version | only if reading it is slow (it is not) | public or staff, as the document | - | a new version |
| An embedding of a ticket's text | the exact text and the embedding model | **yes** (`ta:embedding:v1:<model>:<dimensions>:<hash of the text>`) | none needed: only a caller who has the text can make the key | 24 hours | never wrong; a new model gets a new key |
| A ticket's classification and draft reply | the ticket's text, the prompt and the model | no: each ticket is classified once and the result is stored in PostgreSQL (`ai_runs`) | - | - | - |
| An answer to a question | the question, the documents the caller may read, **the caller's own tickets**, the prompt and model versions | **yes** (`ta:answer:v1:docs=…:model=…:prompt=…:<scope>:g<generation>:<hash of the question>`) | `customer:<id>` or `staff` | 10 minutes | a new ticket or message of that customer (generation + 1); any document change (the docs version in the key) |
| Similar tickets of a ticket | the ticket's vector and the filters | not now: the search takes milliseconds (the databases course's index) | - | - | - |

Rules used here:

1. Put everything that changes the result into the key, including who asks. If two callers may get different answers, their keys must differ.
2. Prefer versions and generations in the key to deleting keys: an old key is never read again and expires by itself.
3. A cache is a copy. The API must give a correct answer when the cache is empty, slow or down.
