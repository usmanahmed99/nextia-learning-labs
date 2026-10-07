# C02: Python for Practical AI Engineering

Data and notebooks for [Python for Practical AI Engineering](https://learning.nextia-ai.com/courses/python/).

| Path | Used in | What it is |
|---|---|---|
| `data/tickets.csv` | Modules 4 to 6, final assignment | 15 synthetic support tickets: 9 valid, 6 with one problem each. |
| `data/tickets.json` | Module 4 | The same tickets as JSON, as a web service sends them. |
| `data/tickets-excel.csv` | Module 5 | The same tickets, saved by a spreadsheet program. |
| `data/tickets-v2.csv`, `data/tickets-v2.json` | Final assignment | 20 tickets in the new format, with `channel` and `subject`. |
| `M06-L01-notebook-discipline/` | Module 6, lesson 1 | A notebook about hidden state and restart-and-run-all. |

The dataset card is [data/dataset.md](data/dataset.md).

## Lesson notebooks

Each folder `Mnn-Lnn-<lesson>/` has the notebook of one lesson, and its solution (`-solution.ipynb`). A notebook has every example, task and check of its lesson. Its first cells make a folder `ticket-cleaner` as at the start of the lesson (with the code of the earlier lessons), download the data files that it needs from this repository with a checksum, and install the packages in the course's versions (httpx 0.28.1, pytest 9.1.1). So you can open any lesson's notebook without the earlier lessons.

| Folder | Lesson |
|---|---|
| `M02-L01-basic-values/` | Basic values |
| `M02-L02-collections/` | Collections |
| `M02-L03-decisions-and-repetition/` | Decisions and repetition |
| `M03-L01-function-contracts/` | Function contracts |
| `M03-L02-modules-and-imports/` | Modules and imports |
| `M03-L03-structured-records/` | Structured records |
| `M04-L01-reading-and-writing-files/` | Reading and writing files |
| `M04-L02-basic-http-client-use/` | Basic HTTP client use |
| `M04-L03-configuration-and-secrets/` | Configuration and secrets |
| `M05-L01-read-failures/` | Read failures |
| `M05-L02-exceptions-and-logging/` | Exceptions and logging |
| `M05-L03-focused-tests/` | Focused tests |
| `M06-L01-notebook-discipline/` | Notebook discipline |
| `M06-L02-command-line-interface/` | Command-line interface |

Module 1 (the terminal, installing Python, virtual environments) and Quality and handoff (ruff, the README, a fresh copy) have no notebook: they are about your own computer. The notebooks are generated; do not edit them by hand.

## Get a data file

In your project folder, with the terminal in `ticket-cleaner`:

```sh
curl -o data/tickets.csv https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C02/data/tickets.csv
```

On Windows, in PowerShell, type `curl.exe` instead of `curl`. You can also open the link in a browser and save the file into your `data` folder.
