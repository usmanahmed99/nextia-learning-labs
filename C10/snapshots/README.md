# Snapshots: resolution-workflow at the start and at the end of each module

Each folder here is the `resolution-workflow` project of [AI Agents and Workflow Orchestration](https://learning.nextia-ai.com/courses/agents/). `start` is the project that you download in Module 1. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The 70 tasks and the practice database (`data/`), the recorded model decisions, three designs on the same ticket: fixed steps, a router and an agent (`workflow.py`, `agent.py`, `loop.py`), the read tools, Grace's rules in code, `tasks`, `show`, `run` (`--trace`). Nothing is written: every design only proposes. | 14 |
| [`end-of-m01`](end-of-m01) | Module 2 | Compare the designs on all tasks: `evaluate.py`, `eval`, `compare` (the proposal only). | 23 |
| [`end-of-m02`](end-of-m02) | Module 3 | Tool contracts (Pydantic arguments, write authorization, a size limit on results) in `tools.py`; a loop that always ends (time, spending cap, repeated calls, errors) in `loop.py`; the usage cap in `config.py`; termination tests. | 35 |
| [`end-of-m03`](end-of-m03) | Module 4 | Long-term memory for a returning customer (`memory.py`); tests for the working context and the plan. | 40 |
| [`end-of-m04`](end-of-m04) | Module 5 | Approval (`approval.py`), checkpoints (`checkpoint.py`), writes with operation IDs and reconciliation (`execute.py`); `approve`, `reject`, `resume`, `trace`, `runs`, `changes`, `reset`; the evaluation checks the database. | 60 |
| [`end-of-m05`](end-of-m05) | Module 6 | Parallel reads and merge rules (`parallel.py`); two workers, an investigator and a resolver (`agent.py`, two prompts). | 64 |
| [`end-of-m06`](end-of-m06) | The final assignment | Results by slice and a strict approver in `eval`; adversarial, permission and recovery tests; an opt-in live test; the full README. The course-end project. | 69 (1 live test deselected) |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live model.
- The virtual environment `.venv` and the folder `work/` (your practice database, saved runs and memory). They are made again when you set up and run a command.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/resolution-workflow` exists, rename it:

   ```sh
   mv resolution-workflow resolution-workflow-old     # Windows: Rename-Item resolution-workflow resolution-workflow-old
   ```

3. Copy the snapshot into a new `resolution-workflow` folder:

   ```sh
   cp -R nextia-learning-labs/C10/snapshots/end-of-m03 resolution-workflow
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C10\snapshots\end-of-m03 resolution-workflow`.
4. Make the virtual environment and run the tests:

   ```sh
   cd resolution-workflow
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m pytest
   python -m resolver run T-80008
   ```

   `end-of-m03` gives `40 passed`.

## Tested

Tested on 2026-10-09 with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot: every snapshot's tests pass, and the stage's first commands run with the mock provider (`run T-80008`, then `run T-90103 --variant fixed`, `eval --variant fixed`, or `run` + `approve` + `eval`). The virtual environment takes about 35 MB. Windows and Linux are not tested.
