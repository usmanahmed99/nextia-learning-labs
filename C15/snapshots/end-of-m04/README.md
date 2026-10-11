# ticket-cleaner

Checks support-ticket records from a CSV file, a JSON file or a web service, and writes a summary report. Every record that is not valid is listed in the report, with the reason.

## Requirements

- Python 3.12 or newer. Check with `python3 --version` (`python --version` on Windows).
- No account. The `remote` input downloads a public file.

## Set up

Do these steps once, in a terminal in this folder.

1. Make a virtual environment:

   ```sh
   python3 -m venv .venv
   ```

   On Windows, type `python` instead of `python3`.
2. Activate it. On macOS and Linux:

   ```sh
   source .venv/bin/activate
   ```

   On Windows (PowerShell): `.venv\Scripts\Activate.ps1`

   The prompt now starts with `(.venv)`. Activate the environment again in each new terminal.
3. Install the exact versions of the dependencies:

   ```sh
   python -m pip install -r requirements-lock.txt
   ```

## Run

```sh
python -m ticket_cleaner data/tickets.csv
```

Expected output (the last lines):

```text
15 rows: 9 valid, 6 rejected.
Report: reports/summary.json
```

The report is `reports/summary.json`. Each rejected record also appears as a `WARNING` line.

The new web form uses other names for some categories, for example `Sign-in` and `Invoice`. The report counts them under its own names (`login`, `billing`); `ticket_cleaner/records.py` lists them.

Options:

| Option | Meaning | Default |
|---|---|---|
| `input` | A `.csv` or `.json` file, or `remote` to download the records | (required) |
| `--status` | Which tickets to count: `open`, `pending` or `closed` | `open` |
| `--category` | Count only this category. Give it again for more categories. Capital letters and spaces around the name do not matter. | every category |
| `--output` | Where to save the report | `reports/summary.json` |

`python -m ticket_cleaner --help` shows the same list.

For example, the billing and shipping teams' open tickets:

```sh
python -m ticket_cleaner data/tickets.csv --category billing --category shipping
```

With `--category`, the report has one more key, `categories`: the chosen names. `valid_records` and `rejected` always describe the whole file.

## Settings

Set these as environment variables. `.env.example` lists them.

| Variable | Meaning | Default |
|---|---|---|
| `TICKETS_URL` | The web service for the input `remote` | The course's public JSON file |
| `TICKETS_API_TOKEN` | The token for that service. Secret: never put it in a file in this folder. | None |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING` or `ERROR` | `WARNING` |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | The report is written. Rejected records are listed in it. |
| `1` | The input could not be read: a missing file, damaged JSON, or a service error. |
| `2` | The command is wrong, for example an unknown option. |

## Work on the code

With the environment active:

```sh
python -m pytest          # run the tests
ruff format .             # format the code
ruff check .              # find common mistakes
```

All three must pass before you share a change.

- `requirements.txt` lists the packages that the project uses directly. `requirements-lock.txt` has the exact version of every package. After you change `requirements.txt`, make the lock file again in a new environment: `python -m pip install -r requirements.txt`, then `python -m pip freeze > requirements-lock.txt`.
- `pyproject.toml` has the settings for ruff and pytest.

## Project layout

```text
ticket_cleaner/      the package
  __main__.py        runs cli.main() for python -m ticket_cleaner
  cli.py             the command: arguments, logging, exit codes
  config.py          settings from environment variables
  files.py           read CSV and JSON, write the report safely
  remote.py          download records from a web service
  records.py         the Ticket and Rejected types
  parsing.py         validation and cleaning
  report.py          the summary
tests/               pytest tests
data/                sample data (synthetic)
```

## Data

`data/tickets.csv` has 15 synthetic tickets from the [Nextia Learning labs](https://github.com/usmanahmed99/nextia-learning-labs/tree/main/C02/data) (CC0 1.0). Nine are valid, and six have one problem each.

`data/web-form-export.csv` has 12 synthetic tickets from the new web form (CC0 1.0). They are all valid.
