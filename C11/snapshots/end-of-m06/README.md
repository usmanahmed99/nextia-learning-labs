# eval-harness

The project of the course *Evaluating and Testing AI Systems* (Nextia Learning), as it is at the end of the course. An evaluation harness for Larkfield's support assistant: it loads a versioned set of test cases, scores the assistant's saved outputs, checks human and model judges, compares a baseline with a candidate, and writes a release report in which every number traces back to its cases.

You need no account and no key. The assistant's outputs and the model judges' verdicts were recorded from real models and are saved in this folder. A live judge (a free local model, or your own key) is optional, and a usage cap in the code stops it after a fixed number of calls.

## The harness

```text
data/cases.jsonl  ->  load and check (dataset.py)  ->  saved outputs of a run (run.py, outputs/)
                  ->  score: decisions, reply criteria, retrieval (scorers/)
                  ->  judge: rubric, people and models, agreement (judge.py, agreement.py)
                  ->  compare: paired differences, bootstrap intervals, slices, repeats (compare.py)
                  ->  decide: blockers and release rules (release.py)  ->  report (report.py)
```

## Files

| Path | What it does |
|---|---|
| `harness/dataset.py` | `Case`, `load_cases()` (the holdout set only when you ask for it), the dataset version (SHA-256 of the file), the inputs version, the checks (one text in two splits, a rule without its label), the coverage table |
| `harness/run.py` | `Run` (system, prompt and its SHA-256, model, dataset version, repeat, time), `make_run_id()`, `load_outputs()` |
| `harness/scorers/decisions.py` | Team accuracy, needs_human precision and recall, the confusion table |
| `harness/scorers/criteria.py` | Phrase rules for the reply (must / must not), in English and French, and where they fail |
| `harness/scorers/retrieval.py` | hit@k, recall@k, precision@k and MRR on saved search results |
| `harness/schema.py` | The assistant's answer schema (from the LLM applications course) |
| `harness/prompts/` | Grace's rubric, the judge prompts (`judge_reference_v1`, `v1b`, `judge_pairwise_v1`), Grace's policy |
| `harness/judge.py` | Judge requests (reference-based and pairwise), parsing, both orders |
| `harness/agreement.py` | Percent agreement and Cohen's kappa |
| `harness/providers.py`, `config.py` | The adapter for the optional live judge: the mock (recordings), a live OpenAI-compatible provider, the usage cap |
| `harness/costs.py` | Dated price table |
| `harness/compare.py` | Per-case measures, bootstrap intervals, paired differences, slices, repeated runs |
| `harness/release.py` | Release rules, blockers, the decision |
| `harness/report.py` | The Markdown release report |
| `harness/feedback.py` | The simulated production log: thumbs, agent edits, drift, a review sample |
| `data/` | The evaluation set and its card (`dataset.md`), the saved search results, the calibration sample, a sample of public human ratings (MT-Bench, CC BY 4.0), the critical-case reviews, the simulated production log |
| `outputs/` | The saved runs: `runs.json` and one file per run |
| `recordings/` | The recorded judge verdicts that the mock replays |
| `tests/` | `pytest` tests |

## Set up

You need Python 3.12 or later. The packages take about 60 MB.

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
python -m pytest                                        # the tests
python -m harness cases                                 # the evaluation set and its version
python -m harness show T-81034 --run baseline           # one case, its labels and a saved output
python -m harness score baseline --by slice             # one run, overall and by slice (dev split)
python -m harness retrieval                             # ranking measures on saved search results
python -m harness judge baseline                        # a recorded model judge scores every reply
python -m harness pairwise baseline candidate           # two runs, both orders: does the order change the verdict?
python -m harness agree data/calibration/reference_ratings.csv my_ratings.csv
python -m harness compare baseline candidate --by slice
python -m harness repeats candidate                     # the same system, 5 runs
python -m harness decide baseline candidate --split holdout
python -m harness report baseline candidate --split holdout --out report.md
```

`baseline` and `candidate` are short names for repeat 1 of each system; `python -m harness runs` lists every run ID.

## A live judge (optional)

1. Copy `.env.example` to `.env`.
2. Choose Ollama (free, local) or a provider with your own key, as the file shows.
3. Add `--live` to `judge` or `pairwise`, or run `python -m pytest -m live`.

The cap (`JUDGE_MAX_CALLS`, default 20, and `JUDGE_MAX_TOKENS`, default 60,000) stops the run before it passes either limit. A live judge gives other verdicts than the recorded ones: models change, and the same model does not give the same answer twice.

## Reset

If your copy is broken, copy the snapshot of the module you finished last from the labs repository (`C11/snapshots/`), make the virtual environment again, and run `python -m pytest`.

## Licence

Code: MIT (`LICENSE`). Data: CC0 1.0, except `data/public/mt_bench_sample.jsonl` (CC BY 4.0, see `data/public/README.md`).
