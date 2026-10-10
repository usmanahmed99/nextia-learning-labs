# Snapshots: ticket-api at the start and at the end of each module

Each folder here is the `ticket-api` project of [Scaling APIs and AI Workloads](https://learning.nextia-ai.com/courses/scaling/). `start` is the project that you download in the first lesson: the end of [Databases and Storage for AI Applications](https://learning.nextia-ai.com/courses/databases/), unchanged. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The databases course's project: PostgreSQL schema, repository, connection pool, files, vectors. | 108 |
| [`end-of-m01`](end-of-m01) | Module 2 | AI work for every new ticket (`POST /v1/tickets`: classify, draft a reply, embed), the simulated AI provider (`python -m simulator`), the Locust workload (`loadtest/locustfile.py`), `scripts/workload.py`, `percentiles.py`, `machine.py`, `breakdown.py`, the result template. | 128 |
| [`end-of-m02`](end-of-m02) | Module 3 | `INTAKE_MODE` (`async`, `thread`, and `blocking`, a mistake made on purpose), `PROVIDER_MAX_CONCURRENCY`, `scripts/stall.py`, `scripts/limits.py`. | 137 |
| [`end-of-m03`](end-of-m03) | Module 4 | The shared cache in Valkey (`ticket_api/cache.py`), answers to questions with keys that include who asks (`POST /v1/answers`), `scripts/cache.py`, `leak_demo.py`, `stampede.py`, `loadtest/questions.py`. | 148 |
| [`end-of-m04`](end-of-m04) | Module 5 | The job queue in PostgreSQL (`014`), the worker (`python -m ticket_api.worker`), job routes, idempotency keys, retries and dead letters, the queue bound and the rate limit; `queue_watch.py`, `duplicate_demo.py`, `send_tickets.py`. | 163 |
| [`end-of-m05`](end-of-m05) | Module 6 | Timeouts, the circuit breaker and the retry budget (`ticket_api/resilience.py`), graceful worker shutdown; `outage_demo.py`, `shutdown_demo.py`, `autoscale.py`. | 172 |
| [`end-of-m06`](end-of-m06) | The final assignment | Load shapes (`loadtest/ramp.py`, `steady.py`, `burst.py`, `soak.py`), `scripts/compare.py`, `scripts/cost.py`, the capacity report. The course-end project. | 176 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env` and `secrets/`. Make them from `.env.example`, as the snapshot's `README.md` says (each snapshot has its own README, for its stage).
- The virtual environment `.venv` and the large data (`data/large/`).
- Your database and your cache: they live in Docker. `python -m scripts.load --reset` loads the data again; `python -m scripts.cache flush` empties the cache.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/ticket-api` exists, rename it:

   ```sh
   mv ticket-api ticket-api-old     # Windows: Rename-Item ticket-api ticket-api-old
   ```

3. Copy the snapshot into a new `ticket-api` folder, and take your `.env` and `secrets/` with you:

   ```sh
   cp -R nextia-learning-labs/C21/snapshots/end-of-m03 ticket-api
   cp ticket-api-old/.env ticket-api/ && cp -R ticket-api-old/secrets ticket-api/
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C21\snapshots\end-of-m03 ticket-api`, then `Copy-Item ticket-api-old\.env ticket-api\` and `Copy-Item -Recurse ticket-api-old\secrets ticket-api\`. If you have no `.env` yet, make it from `.env.example`. From Module 3, `.env` also needs `CACHE_URL` and `TEST_CACHE_URL` (see `.env.example`).
4. Make the virtual environment, bring the database to this stage and run the tests:

   ```sh
   cd ticket-api
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   docker compose up -d db azurite cache  # start to end-of-m02: docker compose up -d db azurite
   python -m scripts.load --reset
   python -m pytest
   ```

   `end-of-m03` gives `148 passed`. `python -m scripts.load --reset` applies the snapshot's migrations and loads the small data again.

   A database that has migrations from a later snapshot cannot go back: `python -m ticket_api.migrate` never undoes a migration. To go back to an earlier snapshot, delete the database first: `docker compose down --volumes`, then `docker compose up -d db azurite cache`.

## Tested

The snapshots are made by a script from one reference project. Each one was checked with Python 3.12 on macOS (Apple silicon), in a new virtual environment, with a new PostgreSQL database (pgvector/pgvector:0.8.7-pg18-trixie) and an empty Valkey (valkey/valkey:9.1.2-trixie): lint, tests and the stage's first commands, with the snapshot's own simulated provider. Windows and Linux are not tested.
