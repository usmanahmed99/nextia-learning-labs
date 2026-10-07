# C04: SQL and Data Preparation for AI

Data, tools and notebooks for [SQL and Data Preparation for AI](https://learning.nextia-ai.com/courses/sql/).

| Path | Used in | What it is |
|---|---|---|
| `get_data.py` | Module 1 onward | Downloads the three CSV files, checks their checksums and builds `larkfield.db`. `--reset` builds it again. |
| `q.py` | Modules 1 to 3 | Runs a SQL query or a `.sql` file on `larkfield.db` (read-only) and prints a table. |
| `data/customers.csv`, `data/tickets.csv`, `data/outcomes.csv` | All modules | The synthetic Larkfield help-desk export of 2026-07-01, with its problems on purpose. |
| `data/tickets-2026-08-01.csv` | Module 6 | The next export, after a schema change. |
| `data/tickets_model.csv` | Module 5 notebook | The prepared modelling table, plus two leaky columns for the exercise. |
| `generate.py` | Module 6 (lineage) | The script that generated the data (seed 2026, standard library only). |
| `M05-L03-fit-transformations/` | Module 5, lesson 3 | A notebook about fitting transformations on training data only, and what leakage does to a score. |

The dataset card is [data/dataset.md](data/dataset.md).

## Set up the practice database

Python 3.12 or later. In a terminal, in your project folder (`ticket-data`):

```sh
curl -O https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C04/get_data.py
curl -O https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C04/q.py
python3 get_data.py
python3 q.py "SELECT COUNT(*) FROM tickets"
```

On Windows, in PowerShell, type `curl.exe` instead of `curl`, and `py` instead of `python3`. The last command prints `1417`.
