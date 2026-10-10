# Dataset card: Larkfield help desk (databases course)

Used by: every lesson of [Databases and Storage for AI Applications](https://learning.nextia-ai.com/courses/databases/); the project's `data/` folder.

| Field | Value |
|---|---|
| Source | Made up for the course by `generate.py` (standard library only, no network, a fixed seed per size). The ticket vectors are made by `embed.py` with an open embedding model. |
| Publisher / creator | Nextia Learning |
| Licence | CC0 1.0 (public domain). The policy documents are the RAG course's documents (also CC0). |
| Attribution text | None needed. |
| Version | 1.0. The same command always writes the same bytes: `SHA256SUMS` in each folder. |
| Files | `small/` and `large/`: `customers.csv`, `tickets.csv`, `messages.csv`, `attachments.csv`, `documents.csv`, `ai_runs.csv`, `counts.json`, `SHA256SUMS`, `ticket_embeddings.f32` / `.ids` / `.json`; `small/files/` has the attachment files. |
| Size | small: 40 customers, 200 tickets, 334 messages, 43 attachments (43 files, 103 KB), 36 documents, 294 AI runs, 200 vectors (0.7 MB in all). large: 20,000 customers, 300,000 tickets, 690,300 messages, 61,853 attachments (no files), 36 documents, 449,734 AI runs, 10,000 vectors (234 MB of CSV; 316 MB in PostgreSQL). |

## What one row means

- `customers`: one customer account. `customer_id` (`C-0001`), a made-up name, an `example.com` email address, `segment` (home, trade, business), `region`, `joined_on`.
- `tickets`: one support request. `ticket_id` (`T-30001`), the customer, `subject` and `body` (the customer's first message), `channel`, `team` (the ticket API's categories: billing, login, shipping, account, other), `priority` (1 is the most urgent), `status` (open, pending, resolved, closed), `created_at`, `updated_at`, `closed_at` (only for resolved and closed tickets).
- `messages`: one message after the first: from an agent or from the customer.
- `attachments`: one file that a customer attached: name, type, size, SHA-256 and the key of the file in object storage. In the small data the files exist (`small/files/<key>`: made-up photos as PNG, made-up receipts as PDF). In the large data they do not: the rows are only metadata.
- `documents`: one version of one policy document (Markdown text, version, dates).
- `ai_runs`: one call to a model for a ticket: the task (`classify` with the keyword classifier, or `draft_reply` with a language model), model, prompt version, tokens in and out, cost in dollars, time in milliseconds, status (ok, error, timeout) and the output.
- `ticket_embeddings.*`: one vector of 384 numbers per ticket, from `intfloat/multilingual-e5-small` (revision `614241f`, MIT licence) on the CPU, from the text `"query: " + subject + "\n" + body`, normalized. Small: every ticket. Large: the newest 10,000 tickets.

## How it relates to the other courses

- `C-0001` to `C-0240` are the customers of the SQL course (same ID, segment in lower case, region and join date). Their names and email addresses are new, made up for this course. The large data adds customers up to `C-20000`.
- The tickets are new: the SQL course's export had no ticket text. Small: `T-30001` to `T-30200` (25 September to 8 October 2026). Large: `T-100001` to `T-400000` (9 October 2025 to 8 October 2026).
- The products are the agents course's catalogue; the documents are the RAG course's policy collection; the models in `ai_runs` are the deployments of the LLM applications course (`chat-small`, `chat-strong`), with its dated prices (checked 8 October 2026).

## Planted on purpose

- **Three orphan messages**, in both sizes: messages whose ticket does not exist (`T-29994`, `T-29997`, `T-29999` in the small data; `T-99994`, `T-99997`, `T-99999` in the large data), left over from test tickets deleted by hand in the old help-desk tool. The schema lessons find them when they add a foreign key.
- **The cost is stored as `real`** at the start (the old tool's type). A later lesson changes it to `numeric`.
- **One very large customer:** in the large data, `C-3835` (a business account) has 4,322 tickets; most customers have fewer than 30.

## Limitations and cautions

- Everything is made up. No real person, ticket, file or receipt is in it. The texts come from about 40 templates, so many tickets are very similar: in the large data's 10,000 vectors there are only 5,484 different texts. Similarity search finds near-copies easily; do not judge an embedding model on this data.
- The large size is a stress fixture: about 800 tickets a day, far more than Larkfield has today (about 45). It is there to make slow queries visible on a laptop.
- Timestamps are in UTC. The course's "today" is 9 October 2026 (the export time is 06:00 UTC).
- Prices, models and token counts are plausible, not measured.
