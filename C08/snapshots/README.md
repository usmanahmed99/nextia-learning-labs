# Snapshots: ticket-assistant at the start and at the end of each module

Each folder here is the `ticket-assistant` project of [Building Reliable Applications with LLM APIs](https://learning.nextia-ai.com/courses/llm-apps/). `start` is the project that you download in the lesson *A first run without an account*. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1, lesson 2 | The mock provider (`assistant/providers.py`), the request (`context.py`, `prompts/v1.md`, `prompts/policy.md`), `python -m assistant analyse`, the 69 tickets, recorded answers without structured output. | 2 |
| [`end-of-m01`](end-of-m01) | Module 2 | The live provider `OpenAICompatibleProvider`, settings from environment variables and `redact()` (`config.py`), `.env.example`, `python -m assistant.raw` (the request as JSON, and plain HTTP), an opt-in live test. | 15 |
| [`end-of-m02`](end-of-m02) | Module 3 | Prompt v2 with the ticket marked as untrusted, `python -m assistant eval` and `evaluate.py`. | 21 |
| [`end-of-m03`](end-of-m03) | Module 4 | The schema (`schema.py`), the two gates (`validate.py`), `orders.py`, the results database (`store.py`), `analyse.py`, `data/orders.sqlite`, recorded structured answers and failures. | 42 |
| [`end-of-m04`](end-of-m04) | Module 5 | The read-only order lookup (`tools.py`) and the bounded tool loop (`loop.py`), recorded tool calls. | 59 |
| [`end-of-m05`](end-of-m05) | Module 6 | Conversation state (`history.py`) and streaming (`stream.py`), recorded streams and a conversation. | 65 |
| [`end-of-m06`](end-of-m06) | The final assignment | Retries with backoff and jitter (`retry.py`), the simulated failing provider (`simulate.py`), the usage log and prices (`usage.py`), the full README. The course-end project. | 76 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live model.
- The virtual environment `.venv`, `results.sqlite` and `logs/`. They are made again when you run the project.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/ticket-assistant` exists, rename it:

   ```sh
   mv ticket-assistant ticket-assistant-old     # Windows: Rename-Item ticket-assistant ticket-assistant-old
   ```

3. Copy the snapshot into a new `ticket-assistant` folder:

   ```sh
   cp -R nextia-learning-labs/C08/snapshots/end-of-m03 ticket-assistant
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C08\snapshots\end-of-m03 ticket-assistant`.
4. Make the virtual environment, run the tests and the first command:

   ```sh
   cd ticket-assistant
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m pytest
   python -m assistant analyse T-80008
   ```

   `end-of-m03` gives `42 passed, 1 deselected` (the deselected test is the opt-in live test).

## Tested

Tested on 2026-10-09 with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot: every snapshot's tests pass, and `python -m assistant analyse T-80008` runs with the mock provider. Windows and Linux are not tested.
