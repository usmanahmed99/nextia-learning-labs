# Snapshots: escalation-service at the end of each module

Each folder here is the `escalation-service` project of [Deploying AI Models for Real Users](https://learning.nextia-ai.com/courses/serving/), as it is after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has |
|---|---|---|
| [`end-of-m01`](end-of-m01) | Module 2 | The contract (`escalation/contract.py`), the bundle loader (`escalation/bundle.py`), `make_bundle.py` and the course's bundle `bundles/escalation-1.0.0`. 18 tests. |
| [`end-of-m02`](end-of-m02) | Module 3 | Settings, scoring, the batch job (`escalation/batch.py`), the job queue (`escalation/jobs.py`) and `data/july_tickets.csv`. 20 tests. |
| [`end-of-m03`](end-of-m03) | Module 4 | The service: `main.py`, `routes.py`, `errors.py`, `security.py`, `pyproject.toml`, and the parity check `parity/check_parity.py`. 42 tests. |
| [`end-of-m04`](end-of-m04) | Module 5 | `Dockerfile`, `.dockerignore`, `requirements-run.txt`, `compose.yaml` with CPU, memory and worker limits, `.env.example`, `bench/bench.py` and `docs/infrastructure.md`. |
| [`end-of-m05`](end-of-m05) | The final assignment | Shadow scoring, `escalation/monitor.py` and `GET /v1/monitor`, `monitoring/outcomes.py`, `training/retrain.py`, the bundle `escalation-1.1.0`, `data/july_labels.csv` and `RELEASES.md`. The retired `1.1.0-rc1` bundle is not here: make it again with `retrain.py` if you need it. |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example`, and put the bundle's digest in `MODEL_SHA256` (the digest of the course's 1.0.0 bundle is `8f233029aa4c896dce1a5b3dfa970cd085088386bbe7784519f15a5b1a433b74`).
- The virtual environment `.venv`, images and containers. Make them again as the lessons say.
- Your own bundles. A snapshot has the course's bundles, with the course's digests.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/escalation-service` exists, rename it. If its containers run, stop them first in the old folder: `docker compose down`.

   ```sh
   mv escalation-service escalation-service-old     # Windows: Rename-Item escalation-service escalation-service-old
   ```

3. Copy the snapshot into a new `escalation-service` folder:

   ```sh
   cp -R nextia-learning-labs/C17/snapshots/end-of-m03 escalation-service
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C17\snapshots\end-of-m03 escalation-service`.
4. Make the virtual environment and run the tests:

   ```sh
   cd escalation-service
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m pytest
   ```

   `end-of-m03` gives `42 passed`.
5. From `end-of-m04` on, make `.env` (`cp .env.example .env`, then fill in `MODEL_SHA256`) and start the container with `docker compose up -d --build --wait`. Check it with `curl http://127.0.0.1:8000/ready` (Windows: `curl.exe`).

## Tested

Tested with Python 3.14.6 and Docker Desktop (Docker Engine 29.6.1) on macOS, Apple silicon, from a new folder for each snapshot: `end-of-m01` 18 tests passed, `end-of-m02` 20, `end-of-m03` to `end-of-m05` 42, without `MODEL_SHA256` in the shell. `end-of-m05`: `docker compose up -d --build --wait` → healthy, `/v1/model` → 1.0.0, `parity/check_parity.py` → 14 of 14. Windows and Linux are not tested.
