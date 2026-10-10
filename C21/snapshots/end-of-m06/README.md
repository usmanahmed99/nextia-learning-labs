# ticket-api: scaling an AI workload

The project of [Scaling APIs and AI Workloads](https://learning.nextia-ai.com/courses/scaling/) (Nextia Learning). It is the ticket API of the API, Docker, CI/CD and databases courses. In this course, every new ticket starts AI work (classify, draft a reply, embed), and the API learns to handle many tickets at once: measured first, then with concurrency, a shared cache, a job queue with workers, limits for overload, failure containment and load tests.

All the data is made up for the course. No real customer, ticket or file is in it. The AI provider is **simulated**: a small local service whose times and quota come from real recorded calls to a hosted model. Its answers are simple; its timing is realistic.

## What you need

- Python 3.12 or later.
- Docker (Docker Desktop on Windows and macOS) for PostgreSQL 18 with pgvector, Azurite (the storage emulator of the databases course) and, from Module 3, Valkey (the cache). Without Docker, see [Without Docker](#without-docker).

You do not need an account, a key or money. Run load tests only against these services on your own computer.

## Set up

macOS and Linux:

```sh
cp .env.example .env              # then change the password in .env (three places)
mkdir -p secrets && echo "local-practice-key" > secrets/api_key.txt
docker compose up -d db azurite cache     # PostgreSQL (127.0.0.1:5432), Azurite (127.0.0.1:10000) and Valkey (127.0.0.1:6379)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m scripts.load            # the migrations, then the small data
python -m pytest
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env       # then change the password in .env (three places)
New-Item -ItemType Directory -Force secrets; Set-Content secrets\api_key.txt "local-practice-key"
docker compose up -d db azurite cache
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.load
python -m pytest
```

Then, in three terminals (venv active in each):

```sh
python -m simulator               # the simulated AI provider, http://127.0.0.1:8300/v1
fastapi dev                       # the API, http://127.0.0.1:8000/docs
python -m ticket_api.worker       # from Module 4: the worker that does the queued AI work
```

Send a ticket:

```sh
curl -X POST http://127.0.0.1:8000/v1/tickets -H "Content-Type: application/json" \
  -d '{"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments for one order."}'
```

**Reset:** `python -m scripts.load --reset` loads the data again (new tickets start at T-500001 again); `python -m scripts.cache flush` empties the cache; `docker compose down --volumes` deletes the database. The simulated provider forgets everything when you stop it.

**Everything in Docker** (the API, the simulated provider, the worker, the database, Azurite and the cache): `docker compose up -d --build`. The API then needs the key in `secrets/api_key.txt` (header `X-API-Key`).

## How a new ticket gets its AI work

`INTAKE_MODE` (in `.env`) chooses:

| Mode | What happens | Module |
|---|---|---|
| `thread` | the endpoint waits for the provider in a worker thread and keeps a database connection the whole time (the first version) | 1 |
| `blocking` | a mistake, made on purpose: the waiting client inside an async endpoint stalls the whole server | 2 |
| `async` | the endpoint awaits the provider; a database connection only for the short save at the end | 2 |
| `queue` (default) | the ticket and a job are saved at once (202); a worker does the AI work; `GET /v1/jobs/{id}` shows the result | 4 |

## Commands

| Command | What it does | Module |
|---|---|---|
| `python -m simulator [--mode normal\|slow\|outage\|quota]` | the simulated AI provider; `POST /admin/mode`, `GET /admin/stats` | 1 |
| `locust -f loadtest/locustfile.py --host http://127.0.0.1:8000 [--headless -u 4 -r 4 -t 60s]` | the load generator: users send new tickets | 1 |
| `python -m scripts.machine` | the computer, for the top of every result | 1 |
| `python -m scripts.workload [--factor 10]` | the workload in numbers, from the tickets in the database | 1 |
| `python -m scripts.percentiles <samples.csv> [--skip 5]` | exact percentiles of a load test (`SAMPLES_CSV=<file>` for Locust) | 1 |
| `python -m scripts.breakdown [--tickets 20] [--concurrency 1]` | where a new ticket's time goes (Server-Timing) | 1 |
| `python -m scripts.stall` | does `/health` still answer while tickets wait for the provider? | 2 |
| `python -m scripts.limits [--processes 4]` | connections and provider calls of all processes together | 2 |
| `locust -f loadtest/questions.py ...` | users ask the help desk's common questions | 3 |
| `python -m scripts.cache stats\|keys\|flush` | look into the shared cache | 3 |
| `python -m scripts.leak_demo` | constructed: a cache key without the caller's identity | 3 |
| `python -m scripts.stampede [--requests 20]` | many requests for one new answer at the same moment | 3 |
| `python -m ticket_api.worker [--once] [--concurrency 4]` | the worker | 4 |
| `python -m scripts.queue_watch` | the queue, one line per second | 4 |
| `python -m scripts.duplicate_demo` | constructed: a repeated request and a repeated delivery | 4 |
| `python -m scripts.send_tickets --rate 5 --seconds 30` | send tickets at a fixed arrival rate | 4 |
| `python -m scripts.outage_demo [--breaker on\|off]` | a simulated outage, with and without a circuit breaker | 5 |
| `python -m scripts.shutdown_demo` | stop a worker gracefully, then kill one (constructed) | 5 |
| `python -m scripts.autoscale [--min 1 --max 6]` | a local autoscaler that starts and stops workers | 5 |
| `locust -f loadtest/ramp.py\|steady.py\|burst.py\|soak.py --headless` | load shapes | 6 |
| `python -m scripts.compare --config "name:VAR=value,..." ...` | compare configurations, several passes each | 6 |
| `python -m scripts.cost` | estimated AI cost per ticket, from the dated prices | 6 |

The databases course's commands still work (`scripts.bench`, `scripts.explain`, `scripts.backup`, ...).

## Settings

In `.env` (see `.env.example`); a variable that is already set wins. The databases course's settings are unchanged.

| Variable | Default | What it does | Module |
|---|---|---|---|
| `PROVIDER_URL`, `PROVIDER_API_KEY` | `http://127.0.0.1:8300/v1`, none | the AI provider (any OpenAI-compatible API) | 1 |
| `PROVIDER_TIMEOUT` | `10` (Modules 1–4: `30`) | seconds for one call | 1, 5 |
| `INTAKE_MODE` | `queue` (see the table above) | how a new ticket gets its AI work | 2, 4 |
| `PROVIDER_MAX_CONCURRENCY` | `0` (no limit) | provider calls in flight per process | 2 |
| `CACHE_URL`, `TEST_CACHE_URL` | none | Valkey for the API and for the tests | 3 |
| `CACHE_TIMEOUT`, `CACHE_TTL_SECONDS`, `CACHE_STAMPEDE_GUARD`, `CACHE_LOCK_SECONDS` | `0.05`, `600`, `true`, `10` | the cache's limits | 3 |
| `QUEUE_MAX`, `RATE_LIMIT_PER_MINUTE` | `500`, `30` | backpressure: queue bound (503), tickets per caller per minute (429) | 4 |
| `WORKER_CONCURRENCY`, `JOB_LEASE_SECONDS`, `JOB_MAX_ATTEMPTS`, `WORKER_POLL_SECONDS`, `RETRY_BASE_SECONDS`, `RETRY_CAP_SECONDS` | `4`, `30`, `5`, `0.5`, `2`, `60` | the worker | 4 |
| `BREAKER_FAILURES`, `BREAKER_OPEN_SECONDS`, `PROVIDER_RETRIES`, `RETRY_BUDGET_RATIO`, `WORKER_DRAIN_SECONDS` | `5`, `30`, `1`, `0.1`, `20` | failure containment and graceful shutdown | 5 |

The tests use their own database (`TEST_DATABASE_URL`, its name ends in `_test`) and their own cache database (`TEST_CACHE_URL`, Valkey database 15), and delete everything in them. Without PostgreSQL or Valkey, those tests are skipped. They use a fake AI provider with no waiting.

## Without Docker

Install PostgreSQL 18 with pgvector as the databases course explains (the installer from postgresql.org, or the PGDG packages on Linux), and Valkey (Linux packages `valkey`; on macOS `brew install valkey`; on Windows, use WSL or Docker). Then, as the `postgres` user in `psql`:

```sql
CREATE ROLE tickets LOGIN SUPERUSER PASSWORD 'your-password';
CREATE DATABASE tickets OWNER tickets;
```

`SUPERUSER` is only for practice on your own computer. This route is not tested.

## Files

| Path | What it is |
|---|---|
| `ticket_api/` | the API. This course adds `ai.py` (the requests to the provider), `provider.py` (its client), `intake.py` (new tickets), `timing.py`, `prices.py`, `cache.py`, `answers.py`, `jobs.py` (the queue's SQL), `job_routes.py`, `worker.py`, `ratelimit.py`, `resilience.py` |
| `simulator/` | the simulated AI provider; `calibration.json` comes from the recorded calls |
| `loadtest/` | the Locust workloads and load shapes |
| `migrations/` | the schema; `013_ai_work.sql`, `014_jobs.sql` are this course's |
| `scripts/` | the commands above |
| `docs/` | `workload.md`, `benchmark-template.md`, `cache-plan.md` (worked examples), `capacity-report.md` (the recommendation of Module 6), and the databases course's storage map and schema |
| `data/` | the made-up help-desk data (from the databases course) |
| `.github/`, `deploy/`, `evaluation/`, `contract/` | from the CI/CD course: the pipeline, the local environments, the AI evaluation gate, the API contract |

Code: MIT licence. Data: CC0.
