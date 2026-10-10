# Dataset card: recorded calls to a hosted AI model

**What it is.** 763 calls to a hosted chat model and an embedding model, made by the course team on 2026-10-10 to calibrate the simulated AI provider of the course project. For each call: the task (`classify`, `draft_reply`, `embed`), the model deployment, the time it was sent, the time to the full answer, the HTTP status, the tokens in and out, the provider's rate-limit headers and, for chat calls, the answer text. No key and no request header is in the files.

**Where it comes from.** The requests are exactly the ones the project sends (`ticket_api/ai.py`), for the first 100 made-up tickets of Larkfield's small practice data (from the databases course). The deployments were Azure OpenAI `chat-small` (gpt-6-luna, 2026-09-22) and `embed-small` (text-embedding-3-small with 384 dimensions), region East US 2. Four phases: one call at a time (`sequential.jsonl`, 300 calls), 16 at a time (`concurrent.jsonl`, 300 calls, 82 refused with HTTP 429), and a burst of replies 40 at a time (`burst.jsonl`, 160 calls, 126 refused). `COST.log` has the estimated cost of each phase (US$0.0111 in total).

**Files.** `recordings/*.jsonl` (one JSON object per line) and `calibration.json`, the project's `simulator/calibration.json`: what a small fitting script made from the recordings (the times of the 100 calls of each task at concurrency 1, a line from characters to tokens, the recorded answers, the quota).

**What it is good for.** Realistic times (median about 0.9 s to classify, 1.1 s to draft a reply, 0.2 s to embed) and a real quota answer (HTTP 429 with `Retry-After: 30` and a much shorter `retry-after-ms`).

**Limits.** One afternoon, one region, one account, 100 tickets: other times and other providers differ. The answers are a model's output for made-up tickets; they are not checked for quality. No outage and no slow period was recorded: the simulator's slow and outage modes are constructed.

**People and privacy.** The tickets and customers are made up. No real person's data is in the requests or the answers.

**Licence.** CC0 1.0.
