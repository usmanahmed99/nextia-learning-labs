# C18 snapshots: ticket-api at the end of each module

Each folder here is the `ticket-api` project of [Docker and Cloud Essentials for AI Developers](https://learning.nextia-ai.com/courses/docker/), as it is after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

Module 1 makes no project files. To start Module 2, use C16's last snapshot, [`C16/snapshots/end-of-m07`](../../C16/snapshots/end-of-m07).

| Snapshot | Use it to start | What it has |
|---|---|---|
| [`end-of-m02`](end-of-m02) | Module 3 | C16's `ticket-api` (version 1.0.0, 17 tests), plus the `Dockerfile` (non-root user `app`), the allowlist `.dockerignore` and `requirements-run.txt`, the exact packages of the image (FastAPI only). |
| [`end-of-m03`](end-of-m03) | Module 4 | Version 1.1.0: settings from files (`API_KEY_FILE`), `REQUIRE_API_KEY`, the optional PostgreSQL history (`ticket_api/history.py`, `GET /v1/history`), `compose.yaml` and `.env.example`. 25 tests. |
| [`end-of-m04`](end-of-m04) | Module 5 | The same code as `end-of-m03`, plus `docs/cloud-design.md`, the cloud design with the resource inventory. |
| [`end-of-m05`](end-of-m05) | The final assignment | `deploy/containerapp.yaml` (the Azure Container Apps settings), `deploy/local-cloud.yaml` (the same settings on your computer) and `DEPLOY.md` (checklist, inventory and clean-up record). |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

A snapshot has only files. It does not have:

- images, containers or volumes. You build them again with the commands in the snapshot's `README.md`;
- `.env` or `secrets/`, so no password and no API key. Make them as the README says (`cp .env.example .env`, then change the password; `printf 'local-dev-key' > secrets/api_key.txt`);
- the virtual environment `.venv`. You need it only to run the tests on your computer;
- any cloud resource or registry login. If you need them, do the steps of Module 5 again.

## Use a snapshot

You need Docker. The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/ticket-api` exists, rename it. You are still in `~/projects`:

   ```sh
   mv ticket-api ticket-api-old           # Windows: Rename-Item ticket-api ticket-api-old
   ```

   If you used Compose with your old project, stop it first, in the old folder: `docker compose down`. The data in the volume `ticket-api_pgdata` stays. It is used again by the new project, because the folder has the same name.
3. Copy the snapshot into a new `ticket-api` folder:

   ```sh
   cp -R nextia-learning-labs/C18/snapshots/end-of-m03 ticket-api
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C18\snapshots\end-of-m03 ticket-api`.
4. Build the image and start it, as the snapshot's `README.md` says. For `end-of-m02`:

   ```sh
   cd ticket-api
   docker build -t ticket-api:1.0.0 .
   docker run --rm -p 127.0.0.1:8000:8000 -e API_KEY=local-dev-key ticket-api:1.0.0
   ```

   From `end-of-m03` on, make `.env` and `secrets/api_key.txt` first, then run `docker compose up -d --build`.
5. Check it in a second terminal:

   ```sh
   curl http://127.0.0.1:8000/health      # Windows: curl.exe
   ```

   The answer is `{"status":"ok"}`.

To run the tests too, make a virtual environment and install `requirements-lock.txt`, as in C16, then run `python -m pytest`.

## Tested

Tested on 2026-10-07 with Docker Desktop 4.81.0 (Docker Engine 29.6.1, Compose 5.2.0) on macOS, Apple silicon, from a new folder for each snapshot. `end-of-m02`: 17 tests passed, the image built, `/health` and `/v1/classify` answered. `end-of-m03`: 25 tests passed, the image built and answered. `end-of-m05`: `docker compose up -d --build` with the database, a classification and its history; `docker compose down --volumes`; then `deploy/local-cloud.yaml` started, and `/docs` gave `404` as configured. Windows and Linux are not tested.
