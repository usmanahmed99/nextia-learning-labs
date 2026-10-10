# Snapshots: ticket-cleaner at the start and at the end of each module

Each folder here is the `ticket-cleaner` project of [AI-Assisted Software Development](https://learning.nextia-ai.com/courses/ai-assisted-dev/). `start` is the project that you download in the first module. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The end of [Python for Practical AI Engineering](https://learning.nextia-ai.com/courses/python/), with one change by a teammate: the web form's category names (`Sign-in`, `Invoice`, `Delivery`) are counted under the report's names. Grace's export `data/web-form-export.csv`. `.env.example`, `LICENSE` (MIT). | 24 |
| [`end-of-m01`](end-of-m01) | Module 2 | `tests/test_baseline.py` (today's report, kept as it is), `ASSISTANT-SCOPE.md` (what an assistant may read, change and run). | 25 |
| [`end-of-m02`](end-of-m02) | Module 3 | The task brief, the bug report and the plan in `docs/tasks/`; one test that the investigation found. | 26 |
| [`end-of-m03`](end-of-m03) | Module 4 | The `--category` option after review (`cli.py`, `report.py`, `README.md`, tests), `docs/review-checklist.md`. | 34 |
| [`end-of-m04`](end-of-m04) | Module 5 | Grace's bug fixed in `parsing.py`, with a regression test and her export as a test. | 39 |
| [`end-of-m05`](end-of-m05) | The final assignment | `--category` uses the same cleaning as the tickets, `DECISIONS.md`, the README's limitations and a test that checks the README, `docs/pull-request.md`. The course-end project. | 42 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

**About Grace's bug:** it is in `start` on purpose, and the course says so. It came with the teammate's change of the category names: the change looks right, and its own test passes. You find it in Module 2 and fix it in Module 4. If you use your own `ticket-cleaner` from the Python course, it does not have the bug: use `start` for this course.

## What a snapshot does not have

- `.venv` and `reports/`. You make them again.
- `.env`. The course does not need it. `.env.example` lists the settings.
- A Git repository. The first module makes one (`git init`), so that you can see every change as a diff.

## Use a snapshot

The steps use `start` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Copy the snapshot to a new folder, `ticket-cleaner-assist` (a different name from your Python course project, so that you keep it):

   ```sh
   cp -R nextia-learning-labs/C15/snapshots/start ticket-cleaner-assist
   ```

   On Windows (PowerShell): `Copy-Item -Recurse nextia-learning-labs\C15\snapshots\start ticket-cleaner-assist`
3. Make the environment and check it:

   ```sh
   cd ticket-cleaner-assist
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements-lock.txt
   python -m pytest
   ```

   On Windows (PowerShell): `python -m venv .venv`, then `.venv\Scripts\Activate.ps1`, then the same `pip` and `pytest` commands.

   The last line of `pytest` shows the number of tests in the table above, for example `24 passed` for `start`.
4. Run the first command of the course:

   ```sh
   python -m ticket_cleaner data/web-form-export.csv
   ```

   Expected: `12 rows: 12 valid, 0 rejected.` and `Report: reports/summary.json`. Open `reports/summary.json`: in `start`, `by_category` has `Billing`, `LOGIN` and `Login` next to `billing` and `login`. That is Grace's bug. From `end-of-m04`, it has `account` 1, `billing` 3, `login` 4 and `shipping` 2.

## Start again from nothing

Delete the folder (`rm -rf ticket-cleaner-assist`; Windows: `Remove-Item -Recurse -Force ticket-cleaner-assist`) and do steps 2 to 4 again. Nothing outside the folder changes.
