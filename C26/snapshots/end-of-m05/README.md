# Design pack: the shared document assistant

This folder is Kwame's design and cost proposal for a document assistant that several shops share. It is the project of the course *AI System Design and Cost Engineering*. You build it one module at a time.

Everything runs on your computer. You need **Python 3.12 or newer** and nothing else: the calculator uses only the Python standard library. You do not need an account or money.

## Set up (once)

macOS and Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

## First commands

```sh
python -m costmodel          # what the pack can calculate now
python -m pytest -q          # the tests: all must pass
```

If something is wrong, download the snapshot of your module again and start from there (the reset path).

## The three kinds of numbers

Every number in this pack is one of three kinds, and the files say which:

| Kind | Where | Example |
|---|---|---|
| **measured** | `measured.toml` (each value names the run it comes from) | chat-small answers in 1.52 s (median) |
| **price** | `prices.toml` (each price names its price page) | US$0.10 per million input tokens |
| **assumption** | `demand.toml`, `design.toml` (a range `[low, base, high]` and the reason) | 800 customers ask a question each day (base) |

Prices change: check the current price page before you use a price in a real proposal.

## What is in the pack

| File or folder | What it is | Module |
|---|---|---|
| `requirements.md` | users, journeys, out of scope, quality attributes with targets | 1 |
| `demand.toml` | demand per tenant as ranges, each verified or assumed | 1 |
| `prices.toml`, `measured.toml` | the price list and the measured values (given) | from the start |
| `architecture/` | container diagram (`container.drawio`, `container.svg`), request flow, ingestion sequence, data and identity flow, `components.toml` | 2 |
| `design.toml` | sizing choices and operating assumptions | 3 (labour 4, recovery and growth 5) |
| `costmodel/` | the calculator | 1 to 6 |
| `decisions/` | failure modes (5), decision records, roadmap, presentation outline (6) | 5 and 6 |
| `tests/` | the calculator's tests | every module |

## Commands

| Command | What it prints | Module |
|---|---|---|
| `python -m costmodel inputs` | how many numbers of each kind | start |
| `python -m costmodel demand` | questions per day per tenant, and the busiest hour | 1 |
| `python -m costmodel components` | every component, its job and its owner | 2 |
| `python -m costmodel workload` | the workload arithmetic, every step | 3 |
| `python -m costmodel costs` | the monthly cost by driver | 3 |
| `python -m costmodel units` | cost per question, per document change, per tenant | 3 |
| `python -m costmodel scenarios` | low, base and high, now and in month 12 | 3 |
| `python -m costmodel sensitivity` | what if usage doubles, answers get longer, prices rise | 3 |
| `python -m costmodel export` | `costs.csv` for a spreadsheet, `explorer.json` | 3 |
| `python -m costmodel options` | model routing, caching and batching | 4 |
| `python -m costmodel buildbuy` | managed services or your own, with people's time | 4 |
| `python -m costmodel recovery` | RTO and RPO of two backup plans | 5 |
| `python -m costmodel growth` | the growth signals month by month | 5 |
| `python -m costmodel check` | the whole pack, before you hand it in | 6 |

Add `--scenario low` or `--scenario high`, and `--month 12`, to see another case.

A spreadsheet is optional. `python -m costmodel export` writes `costs.csv` with every driver for every scenario; the sums in a spreadsheet are the same as the calculator's.

## Licence

MIT (see `LICENSE`). The measured values come from the course team's runs on the RAG course's documents and questions (CC0).
