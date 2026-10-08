# Snapshots: ticket-api at the end of each module

Each folder here is the `ticket-api` project of [Build and Deploy Your First API](https://learning.nextia-ai.com/courses/api/), as it is after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

Module 1 makes no project, so the first snapshot is the end of Module 2.

| Snapshot | Use it to start | What it has |
|---|---|---|
| [`end-of-m02`](end-of-m02) | Module 3 | The package `ticket_api` with `main.py`, `models.py`, `routes.py` and `classifier.py`: `GET /health` and `POST /classify`. The test bodies in `requests/`, `README.md`, `.gitignore`, `requirements.txt` and `requirements-lock.txt` (FastAPI only). No tests yet. |
| [`end-of-m03`](end-of-m03) | Module 4 | The routes under `/v1`, with `GET /v1/categories`. One error shape in `errors.py`, unknown fields rejected, and CORS from `ALLOWED_ORIGINS`. The test page in `browser-test/`, and two more bodies in `requests/`. No tests yet. |
| [`end-of-m04`](end-of-m04) | Module 5 | The documented API (version `1.0.0`) and the `SHOW_DOCS` setting. pytest and httpx2 in the requirements, `ticket_api/export_contract.py`, the reviewed contract `contract/openapi.json`, and `tests/test_contract.py`: 2 tests. |
| [`end-of-m05`](end-of-m05) | Module 6 | The same code as `end-of-m04`, plus `postman/`: the collection (6 requests, 24 checks) and the Local Postman environment. |
| [`end-of-m06`](end-of-m06) | Module 7 | `config.py`, `create_app`, request IDs and logs, the `503` for a classifier that is down, the API key (`security.py`), the body-size limit and the time limit. 16 tests. The collection has 7 requests and 28 checks. |
| [`end-of-m07`](end-of-m07) | The final assignment | `pyproject.toml`, `GET /ready`, 17 tests, the collection with 8 requests and 31 checks, the Local and Deployed Postman environments, and the README section about the deployed service. |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks, except where a later lesson uses them: the three failure requests in the Postman collection, from Module 5.

## What a snapshot does not have

A snapshot has only files. It does not have:

- the virtual environment `.venv`, or caches. You make the environment in the steps below;
- an API key, or a `.env` file. Use `API_KEY=local-dev-key` on your computer, as in the lessons;
- your Postman account. The collection and the Postman environments are files in `postman/`. To use them in the Postman app, import them (**Import**, then select the files);
- your FastAPI Cloud app, its settings, or the link file `.fastapicloud/cloud.json`. If you need a deployed app, do the steps of [Publish safely](https://learning.nextia-ai.com/courses/api/m07/publish-safely/) again.

## Use a snapshot

You need Python 3.12 or newer. The steps use `end-of-m04` as an example. Use the name of your snapshot.

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

3. Copy the snapshot into a new `ticket-api` folder:

   ```sh
   cp -R nextia-learning-labs/C16/snapshots/end-of-m04 ticket-api
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C16\snapshots\end-of-m04 ticket-api`. If you used the ZIP file, the folder is `nextia-learning-labs-main`, not `nextia-learning-labs`.
4. Move into the project, then make and activate a virtual environment:

   ```sh
   cd ticket-api
   python3 -m venv .venv                  # Windows: python -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   ```

5. Install the exact versions from the lock file:

   ```sh
   python -m pip install -r requirements-lock.txt
   ```

6. From `end-of-m04` on, run the tests. Every test passes:

   ```sh
   python -m pytest
   ```

7. Start the API as the README says, and check it in a second terminal:

   ```sh
   fastapi dev ticket_api/main.py         # end-of-m07: fastapi dev
   curl http://127.0.0.1:8000/health      # Windows: curl.exe
   ```

   The answer is `{"status":"ok"}`.

If you use a snapshot from the end of Module 5 or later, also run the Postman collection, as in [Tests and repeatable runs](https://learning.nextia-ai.com/courses/api/m05/tests-and-repeatable-runs/). From `end-of-m06` on, start the API with `API_KEY=local-dev-key`, and add `--env-var "apiKey=local-dev-key"` to the command.

## Tested

Tested on 2026-10-07 with Python 3.14.6 on macOS, from a new folder for each snapshot: install from `requirements-lock.txt`, `python -m pytest`, then `fastapi dev` with a request to `/health` and `/v1/classify`. Results: `end-of-m02` and `end-of-m03` have no tests; `end-of-m04` and `end-of-m05` 2 passed; `end-of-m06` 16 passed; `end-of-m07` 17 passed. The collections ran with no failures against `fastapi run` (6, 7 and 8 requests; 24, 28 and 31 checks), with newman 6.2.2, which runs the same collection format as the Postman CLI. Windows is not tested.
