# Snapshots: eval-harness at the start and at the end of each module

Each folder here is the `eval-harness` project of [Evaluating and Testing AI Systems](https://learning.nextia-ai.com/courses/evals/). `start` is the project that you download in the lesson *Choose evaluation layers*. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1, lesson 2 | The evaluation set (`data/cases.jsonl`, 271 cases) and its card, `python -m harness cases` and `show`. | 3 |
| [`end-of-m01`](end-of-m01) | Module 2 | The baseline's saved run with its run ID (`run.py`, `outputs/`), the decision scorers (`scorers/decisions.py`), the release rules in words (`release.py`), `runs` and `score`. | 8 |
| [`end-of-m02`](end-of-m02) | Module 3 | The dataset checks: versions, splits, a ticket copied between splits (`dataset.py`), `coverage`. | 13 |
| [`end-of-m03`](end-of-m03) | Module 4 | The reply checks (`scorers/criteria.py`), ranking measures on saved search results (`scorers/retrieval.py`), results by slice (`compare.py`), `score --by`, `retrieval`. | 18 |
| [`end-of-m04`](end-of-m04) | Module 5 | The rubric and the judge prompts, agreement and Cohen's kappa (`agreement.py`), model judges and their recorded verdicts (`judge.py`, `recordings/`), the adapter with a usage cap (`providers.py`, `config.py`), the calibration sample, the public MT-Bench sample, the candidate's saved run, `judge`, `pairwise`, `agree`, `public`. | 34 |
| [`end-of-m05`](end-of-m05) | Module 6 | Bootstrap intervals and paired differences (`compare.py`), blockers and the release decision (`release.py`), the repeated runs, `compare`, `repeats`, `decide`. | 101 |
| [`end-of-m06`](end-of-m06) | The final assignment | The report (`report.py`), the simulated production log (`feedback.py`), the regression and live tests, the full README. The course-end project. | 106 (1 live test skipped) |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live judge.
- The virtual environment `.venv`. Make it again when you set up (see the snapshot's README).

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/eval-harness` exists, rename it:

   ```sh
   mv eval-harness eval-harness-old     # Windows: Rename-Item eval-harness eval-harness-old
   ```

3. Copy the snapshot:

   ```sh
   cp -r nextia-learning-labs/C11/snapshots/end-of-m03 eval-harness     # Windows: Copy-Item -Recurse nextia-learning-labs\C11\snapshots\end-of-m03 eval-harness
   ```

4. Make the virtual environment and install the packages, as in the snapshot's README.
5. Check it: `python -m pytest`. The last line says how many tests passed; it must match the table above.
