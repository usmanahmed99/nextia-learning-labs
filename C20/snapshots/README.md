# Snapshots: ticket-api at the start and at the end of each module

Each folder here is the `ticket-api` project of [Databases and Storage for AI Applications](https://learning.nextia-ai.com/courses/databases/). `start` is the project that you download in the first lesson: the project of the CI/CD course, plus the help-desk data, its tables and the loader. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The help-desk data (`data/`), its tables (`migrations/004_help_desk_tables.sql`, primary keys only), the loader `python -m scripts.load`, `.env` support, and test fixtures that make their own database. | 34 |
| [`end-of-m01`](end-of-m01) | Module 2 | The storage map (`docs/storage-map.md`) and `scripts/embed.py`, which makes the ticket vectors again from the text (optional: needs `requirements-embed.txt`). | 34 |
| [`end-of-m02`](end-of-m02) | Module 3 | The schema diagram (`docs/schema.md`); the rules: keys, unique, `NOT NULL`, checks and foreign keys (`005`), the deliberate copy of the message counts (`006`); the lost-update demo `scripts/lost_update.py`. | 53 |
| [`end-of-m03`](end-of-m03) | Module 4 | The repository layer (`ticket_api/repository.py`), the ticket endpoints, the connection pool (`ticket_api/db.py`), safer migrations (checksums, lock timeout, no-transaction files), the cost as `numeric` (`007`); `injection_demo`, `pool_demo`, `bench`, `rehearse`. The ticket list still pages with OFFSET and sends 41 queries per page. | 79 |
| [`end-of-m04`](end-of-m04) | Module 5 | The measured indexes (`008`), the ticket list with keyset pages and one query, `scripts/explain.py`. | 87 |
| [`end-of-m05`](end-of-m05) | The final assignment | Files through signed URLs in Azurite (`ticket_api/files.py`, `attachments.py`, `009`), vector versions and the HNSW index (`010`, `011`), similar tickets, erasure and its outbox (`012`); `backup`, `restore_drill`, `erase_customer`, `scan`. The course-end project. | 108 (+1 with `pytest -m azurite`) |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env` and `secrets/`. Make them from `.env.example`, as the project's `README.md` says.
- The virtual environment `.venv`, the large data (`data/large/`) and your backups (`backups/`). They are made again when you set up and run the commands.
- Your database and your files in Azurite: they live in Docker volumes. `python -m scripts.load --reset` loads the data again.

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
   cp -R nextia-learning-labs/C20/snapshots/end-of-m03 ticket-api
   cp ticket-api-old/.env ticket-api/ && cp -R ticket-api-old/secrets ticket-api/
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C20\snapshots\end-of-m03 ticket-api`, then `Copy-Item ticket-api-old\.env ticket-api\` and `Copy-Item -Recurse ticket-api-old\secrets ticket-api\`. If you have no `.env` yet, make it from `.env.example`.
4. Make the virtual environment, bring the database to this stage and run the tests:

   ```sh
   cd ticket-api
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   docker compose up -d db                # end-of-m05: docker compose up -d db azurite
   python -m scripts.load --reset
   python -m pytest
   ```

   `end-of-m03` gives `79 passed`. `python -m scripts.load --reset` applies the snapshot's migrations and loads the small data again.

   A database that has migrations from a later snapshot cannot go back: `python -m ticket_api.migrate` never undoes a migration. To go back to an earlier snapshot, delete the database first: `docker compose down --volumes`, then `docker compose up -d db`.

## Tested

The snapshots are made by a script from one reference project. Each one was checked with Python 3.12 on macOS (Apple silicon), in a new virtual environment and with a new PostgreSQL database (pgvector/pgvector:0.8.7-pg18-trixie): lint, tests and the stage's first commands. Windows and Linux are not tested.
