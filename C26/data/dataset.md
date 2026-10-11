# Dataset card: recorded model calls and list prices for the design pack

Used by: the course [AI System Design and Cost Engineering](https://learning.nextia-ai.com/courses/system-design/) (the values in the design pack's `measured.toml` and `prices.toml` come from these files).

| Field | Value |
|---|---|
| Source | calls made by the course team to hosted models; the public Azure Retail Prices API (`https://prices.azure.com/api/retail/prices`) |
| Publisher / creator | Nextia Learning course team |
| Licence | CC0 1.0 (the recorded calls); the price rows are public price-list data from Microsoft, kept here only to show where each price in `prices.toml` comes from |
| Attribution text | none needed |
| Version or access date | the price list's read time is in `prices-azure.json` (`read_at`); prices change, so check the current page |
| Files used | `routing_calls.jsonl`, `requests_calls.jsonl`, `prices-azure.json`, kept here: yes |
| SHA-256 | `SHA256SUMS` |
| Size | 268 rows (one call each) + 231 rows (390 calls: a batching row adds up the calls of one document); 1,112 price rows; 0.8 MB |

## What one row means

- `routing_calls.jsonl`: one question of the RAG course's 67 questions, answered by one model (`chat-small` or `chat-strong`) in one pass (2 passes). The request is the RAG course's recorded request for its best search results: the same passages, prompt and JSON schema for both models. Fields: question ID, model, pass, HTTP status, time to the full answer in seconds, tokens in and out, the cost at the list price, the model version that answered, and the answer (JSON with claims and cited passage IDs).
- `requests_calls.jsonl`: one call of the assistant's other request types: `question_embedding` (each of the 67 questions), `ingest` (all chunks of one document in one embedding call; 36 documents), `batching` (8 long documents embedded chunk by chunk and in one call, 3 passes), `summary` (each document summarized by `chat-small` and by `chat-strong`), `prompt_cache` (one long and one normal request sent 4 times; the tokens the provider reported as cached).
- `prices-azure.json`: for each query to the price API, the exact filter and URL, and the rows (product, meter, unit, retail price, the first unit of the tier).

## Why this dataset

The course compares designs with numbers. A cost model is only as good as its inputs, so every measured input comes from a real call, and every price from a public price list. The routing calls answer one question that guesses cannot: does a stronger model answer these questions better?

## Changes we made

None to the calls. The API key and the request headers were never written to the files.

## Limitations and cautions

- One account, one region (East US 2), one afternoon; one question at a time. Other times, regions and loads give other latencies.
- 67 questions about one small, made-up shop. A different question set can rank the models differently. Correct means "passes the RAG course's automatic checks"; a few answers marked wrong are right in other words.
- The documents, questions and customers are made up for the courses. No real person's data is in the files.
- The prices are list prices before tax, discounts or reservations, read once. Prices change.
