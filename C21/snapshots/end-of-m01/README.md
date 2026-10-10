# ticket-api: scaling an AI workload

The project of [Scaling APIs and AI Workloads](https://learning.nextia-ai.com/courses/scaling/) (Nextia Learning). It is the ticket API of the API, Docker, CI/CD and databases courses. In this course, every new ticket starts AI work (classify, draft a reply, embed), and the API learns to handle many tickets at once: measured first, then with concurrency, a shared cache, a job queue with workers, limits for overload, failure containment and load tests.

This copy is the project at the end of Module 1; the next modules add to it. All the data is made up for the course. No real customer, ticket or file is in it. The AI provider is **simulated**: a small local service whose times and quota come from real recorded calls to a hosted model. Its answers are simple; its timing is realistic.

## What you need

- Python 3.12 or later.
- Docker (Docker Desktop on Windows and macOS) for PostgreSQL 18 with pgvector, Azurite (the storage emulator of the databases course) and, from Module 3, Valkey (the cache). Without Docker, see [Without Docker](#without-docker).

You do not need an account, a key or money. Run load tests only against these services on your own computer.

## Set up

macOS and Linux:

```sh
cp .env.example .env              # then change the password in .env (three places)
mkdir -p secrets && echo "local-practice-key" > secrets/api_key.txt
docker compose up -d db azurite    # PostgreSQL (127.0.0.1:5432) and Azurite (127.0.0.1:10000)
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
docker compose up -d db azurite
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
```

Send a ticket:

```sh
curl -X POST http://127.0.0.1:8000/v1/tickets -H "Content-Type: application/json" \
  -d '{"customer_id": "C-0022", "subject": "Charged twice", "body": "Two payments for one order."}'
```

**Reset:** `python -m scripts.load --reset` loads the data again (new tickets start at T-500001 again); `docker compose down --volumes` deletes the database. The simulated provider forgets everything when you stop it.

**Everything in Docker** (the API, the simulated provider, the database and Azurite): `docker compose up -d --build`. The API then needs the key in `secrets/api_key.txt` (header `X-API-Key`).

## How a new ticket gets its AI work

The endpoint waits for the provider in a worker thread, and it keeps a database connection the whole time: one transaction saves the ticket and its AI results together. Module 2 measures what this costs and adds other ways (`INTAKE_MODE`).
## Commands

| Command | What it does | Module |
|---|---|---|
| `python -m simulator [--mode normal\|slow\|outage\|quota]` | the simulated AI provider; `POST /admin/mode`, `GET /admin/stats` | 1 |
| `locust -f loadtest/locustfile.py --host http://127.0.0.1:8000 [--headless -u 4 -r 4 -t 60s]` | the load generator: users send new tickets | 1 |
| `python -m scripts.machine` | the computer, for the top of every result | 1 |
| `python -m scripts.workload [--factor 10]` | the workload in numbers, from the tickets in the database | 1 |
| `python -m scripts.percentiles <samples.csv> [--skip 5]` | exact percentiles of a load test (`SAMPLES_CSV=<file>` for Locust) | 1 |
| `python -m scripts.breakdown [--tickets 20] [--concurrency 1]` | where a new ticket's time goes (Server-Timing) | 1 |

The databases course's commands still work (`scripts.bench`, `scripts.explain`, `scripts.backup`, ...).

## Settings

In `.env` (see `.env.example`); a variable that is already set wins. The databases course's settings are unchanged.

| Variable | Default | What it does | Module |
|---|---|---|---|
| `PROVIDER_URL`, `PROVIDER_API_KEY` | `http://127.0.0.1:8300/v1`, none | the AI provider (any OpenAI-compatible API) | 1 |
| `PROVIDER_TIMEOUT` | `30` (Module 5: `10`) | seconds for one call | 1 |

The tests use their own database (`TEST_DATABASE_URL`, its name ends in `_test`), and delete everything in it. Without PostgreSQL, those tests are skipped. They use a fake AI provider with no waiting.

## Without Docker

Install PostgreSQL 18 with pgvector as the databases course explains (the installer from postgresql.org, or the PGDG packages on Linux). Then, as the `postgres` user in `psql`:

```sql
CREATE ROLE tickets LOGIN SUPERUSER PASSWORD 'your-password';
CREATE DATABASE tickets OWNER tickets;
```

`SUPERUSER` is only for practice on your own computer. This route is not tested.

## Files

| Path | What it is |
|---|---|
| `ticket_api/` | the API. This course adds `ai.py` (the requests to the provider), `provider.py` (its client), `intake.py` (new tickets), `timing.py`, `prices.py` |
| `simulator/` | the simulated AI provider; `calibration.json` comes from the recorded calls |
| `loadtest/` | the Locust workloads and load shapes |
| `migrations/` | the schema; `013_ai_work.sql` is this course's |
| `scripts/` | the commands above |
| `docs/` | `workload.md`, `benchmark-template.md` (worked examples), and the databases course's storage map and schema |
| `data/` | the made-up help-desk data (from the databases course) |
| `.github/`, `deploy/`, `evaluation/`, `contract/` | from the CI/CD course: the pipeline, the local environments, the AI evaluation gate, the API contract |

Code: MIT licence. Data: CC0.
