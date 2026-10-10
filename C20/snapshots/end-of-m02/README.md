# ticket-api: storage for an AI application

The project of [Databases and Storage for AI Applications](https://learning.nextia-ai.com/courses/databases/) (Nextia Learning). It is the ticket API of the API, Docker and CI/CD courses. In this course, it gets a real storage design: PostgreSQL with rules that protect the data, a connection pool, measured indexes, files in object storage, vectors for similar tickets, and backups that are tested.

All the data is made up for the course. No real customer, ticket or file is in it.

## What you need

- Python 3.12 or later.
- PostgreSQL 18 with the pgvector extension. The easy way is Docker (Docker Desktop on Windows and macOS). Without Docker, see [Without Docker](#without-docker).
- From Module 5: Azurite, an emulator of Azure Blob Storage, in Docker.

You do not need an account, a key or money.

## Set up

macOS and Linux:

```sh
cp .env.example .env              # then change the password in .env (three places)
mkdir -p secrets && echo "local-practice-key" > secrets/api_key.txt
docker compose up -d db           # PostgreSQL with pgvector, on 127.0.0.1:5432
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
docker compose up -d db
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m scripts.load
python -m pytest
```

`python -m scripts.load` prints the number of rows in each table. Run the API with `fastapi dev`, and open http://127.0.0.1:8000/docs.

**Reset:** `python -m scripts.load --reset` deletes the help-desk data and loads it again. `docker compose down --volumes` deletes the whole database (and, from Module 5, the files in Azurite).

**The large data** (300,000 tickets, for the performance lessons): `python -m scripts.load --size large --reset`. The first time, it makes the data on your computer (`data/generate.py`, about 15 seconds) and downloads the ticket vectors (15 MB). Go back to the small data with `python -m scripts.load --reset`.

## Without Docker

Install PostgreSQL 18 (the installer from postgresql.org on Windows and macOS; the PGDG packages on Linux) and pgvector (on Linux, the package `postgresql-18-pgvector`; on Windows and macOS, see the pgvector installation notes). Then, as the `postgres` user in `psql`:

```sql
CREATE ROLE tickets LOGIN SUPERUSER PASSWORD 'your-password';
CREATE DATABASE tickets OWNER tickets;
```

`SUPERUSER` is only for practice on your own computer: the migrations create the `vector` extension, and the tests create and delete their own database. Put the same password in `.env`. Azurite also runs without Docker (`npm install -g azurite`). This route is not tested.

## Commands

| Command | What it does | Module |
|---|---|---|
| `python -m scripts.load [--size large] [--reset]` | apply the migrations and load the data | 1 |
| `python -m scripts.embed --check` / `--rebuild` | make the ticket vectors again from the text (needs `requirements-embed.txt`) | 1 |
| `python -m scripts.lost_update [--lock \| --atomic]` | two sessions update the same ticket | 2 |
| `python -m scripts.injection_demo "x' OR '1'='1"` | a query built from strings, then with a parameter | 3 |
| `python -m scripts.pool_demo connect \| exhaust \| leak \| rollback` | what a connection pool does | 3 |
| `python -m scripts.bench [--pool off] [--concurrency 16]` | measure the ticket list under a fixed workload | 3, 4 |
| `python -m ticket_api.migrate [--status]` | apply the migrations | 3 |
| `python -m scripts.rehearse [--from 005]` | rehearse migrations on a copy with the large data | 3 |
| `python -m scripts.explain queue [--team login]` | the query plan of the ticket list | 4 |
| `python -m scripts.backup` | back up the database, with a manifest | 5 |
| `python -m scripts.restore_drill backups/<file>.dump` | restore into a new database and check it | 5 |
| `python -m scripts.erase_customer C-0012 [--dry-run]` | delete a customer's data everywhere | 5 |
| `python -m scripts.scan [--fix]` | find orphan files, missing files and stale vectors | 5 |

The tests use their own database (`TEST_DATABASE_URL`; its name ends in `_test`) and delete everything in it. They need PostgreSQL; without it, the database tests are skipped. `pytest -m azurite` also runs the test against Azurite.

## Files

| Path | What it is |
|---|---|
| `ticket_api/` | the API; from Module 3: `repository.py` (every SQL statement), `db.py` (the pool), `tickets.py`; from Module 5: `files.py` (the object-storage contract), `attachments.py` |
| `migrations/` | the schema, as numbered SQL files; `ticket_api/migrate.py` applies them |
| `data/` | the made-up help-desk data: `generate.py`, the small data, and the large data once you make it |
| `scripts/` | the commands above |
| `docs/` | the storage map (Module 1) and the schema diagram (Module 2) |
| `.github/`, `deploy/`, `evaluation/`, `contract/` | from the CI/CD course: the pipeline, the local environments, the AI evaluation gate, the API contract |

Code: MIT licence. Data: CC0.
