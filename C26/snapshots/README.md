# Snapshots: the design pack at the start and at the end of each module

Each folder here is the design pack of [AI System Design and Cost Engineering](https://learning.nextia-ai.com/courses/system-design/). `start` is the pack that you download in the first lesson. The others are the pack after the last lesson of one module. If your pack is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The price list (`prices.toml`) and the measured values (`measured.toml`), the calculator's input checks and its commands, a requirements template, a demand template. | 6 |
| [`end-of-m01`](end-of-m01) | Module 2 | `requirements.md` (journeys, out of scope, quality attributes), `demand.toml` (four tenants as ranges, each value verified or assumed), `python -m costmodel demand`. | 12 |
| [`end-of-m02`](end-of-m02) | Module 3 | `architecture/`: the container diagram (draw.io and SVG), the request flow, the ingestion sequence, the data and identity flow, `components.toml`; `python -m costmodel components`. | 16 |
| [`end-of-m03`](end-of-m03) | Module 4 | `design.toml`; the workload arithmetic, the cost model by driver, unit economics, scenarios, sensitivity and the CSV export. | 35 |
| [`end-of-m04`](end-of-m04) | Module 5 | Model routing, caching and batching (`python -m costmodel options`), build versus buy (`python -m costmodel buildbuy`); `design.toml` gets a cache and `[labour]`. | 42 |
| [`end-of-m05`](end-of-m05) | Module 6 | `decisions/failure-modes.md`, recovery objectives (`python -m costmodel recovery`), the growth signals (`python -m costmodel growth`). | 46 |
| [`end-of-m06`](end-of-m06) | The final assignment | Five architecture decision records and their template, the roadmap, the presentation outline, `python -m costmodel check`. The course-end pack. | 49 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own pack. If `~/projects/design-pack` exists, rename it:

   ```sh
   mv design-pack design-pack-old     # Windows: Rename-Item design-pack design-pack-old
   ```

3. Copy the snapshot into a new `design-pack` folder:

   ```sh
   cp -R nextia-learning-labs/C26/snapshots/end-of-m03 design-pack
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C26\snapshots\end-of-m03 design-pack`.
4. Make the virtual environment and run the tests:

   ```sh
   cd design-pack
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements-dev.txt
   python -m pytest -q
   python -m costmodel
   ```

   `end-of-m03` gives `35 passed`.

## Tested

The snapshots are made by a script from one reference pack. Each one was checked with Python 3.12 on macOS (Apple silicon), in a new virtual environment: lint, tests and the stage's first commands. Windows and Linux are not tested.
