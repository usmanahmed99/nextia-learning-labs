# eval-harness

The project of the course *Evaluating and Testing AI Systems* (Nextia Learning). You build it module by module: an evaluation harness for Larkfield's support assistant. It loads a versioned set of test cases, scores the assistant's saved outputs, checks human and model judges, compares two versions of the assistant and writes a release report.

You need no account and no key. Every output of the assistant was recorded from a real model and is saved in this folder.

## Files now

| Path | What it does |
|---|---|
| `harness/dataset.py` | Loads the evaluation set (`data/cases.jsonl`) and gives it a version |
| `harness/__main__.py` | The command line: `python -m harness ...` |
| `data/` | The evaluation set, its card (`dataset.md`) and Grace's policy |
| `tests/` | `pytest` tests |

Later modules add the saved runs (`outputs/`), the scorers, the judges, the comparison and the report. The README of the last snapshot describes every file.

## Set up

You need Python 3.12 or later.

macOS and Linux:

```sh
cd eval-harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd eval-harness
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```sh
python -m pytest                  # the tests
python -m harness cases           # the evaluation set and its version
python -m harness show T-81034    # one case and its labels
```

## Reset

If your copy is broken, copy the snapshot of the module you finished last from the labs repository (`C11/snapshots/`), make the virtual environment again, and run `python -m pytest`.

## Licence

Code: MIT (`LICENSE`). Data: CC0 1.0.
