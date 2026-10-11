# Snapshots: support-mcp at the start and at the end of each module

Each folder here is the `support-mcp` project of [MCP: Connect AI Applications to Tools and Data](https://learning.nextia-ai.com/courses/mcp/). `start` is the project that you download in the first lesson. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The synthetic data and the business service: search and ticket lookup inside one organization (`support_mcp/knowledge.py`). No MCP yet. | 8 |
| [`end-of-m01`](end-of-m01) | Module 2 | The MCP Python SDK (pinned), the smallest server (`examples/hello_server.py`), `scripts/participants.py`, `scripts/versions.py`, the integration map. | 13 |
| [`end-of-m02`](end-of-m02) | Module 3 | The capability contracts (`support_mcp/contracts.py`) and the capability catalog. | 20 |
| [`end-of-m03`](end-of-m03) | Module 4 | The MCP server on stdio (`python -m support_mcp`): two read-only tools, the policy resources, the prompt; `scripts/trace.py`. | 40 |
| [`end-of-m04`](end-of-m04) | Module 5 | The AI application (`python -m host`) with a mock model, its checks, timeouts and limits. | 49 |
| [`end-of-m05`](end-of-m05) | Module 6 | Streamable HTTP with access tokens (`python -m support_mcp --http`), the practice identity provider (`python -m idp`), `scripts/attempts.py`, `scripts/oauth_login.py` (the sign-in flow with the SDK's OAuth client). | 68 |
| [`end-of-m06`](end-of-m06) | Module 7 | Tool results as untrusted data, the refund proposal (`propose_refund`) and its approval (`python -m support_mcp.approvals`). | 84 |
| [`end-of-m07`](end-of-m07) | The final assignment | The contract file and its test, the compatibility matrix (`scripts/compat.py`), logs without secrets, `scripts/latency.py`, `scripts/tee.py`. The course-end project. | 91 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- The virtual environment `.venv`.
- `.idp/` (your practice signing key: `python -m idp init` makes it) and `.support/` (your refund proposals).

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/support-mcp` exists, rename it:

   ```sh
   mv support-mcp support-mcp-old     # Windows: Rename-Item support-mcp support-mcp-old
   ```

3. Copy the snapshot into a new `support-mcp` folder:

   ```sh
   cp -R nextia-learning-labs/C28/snapshots/end-of-m03 support-mcp
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C28\snapshots\end-of-m03 support-mcp`.
4. Make the virtual environment and run the tests:

   ```sh
   cd support-mcp
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: py -m venv .venv, then .venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   python -m pytest -q
   ```

   `end-of-m03` gives `40 passed`.

## Tested

The snapshots are made by a script from one reference project. Each one was checked with Python 3.12 on macOS (Apple silicon), in a new virtual environment: lint, tests and the stage's first commands. Windows and Linux are not tested.
