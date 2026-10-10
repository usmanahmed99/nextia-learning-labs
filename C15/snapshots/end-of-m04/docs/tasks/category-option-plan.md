# Plan: the --category option

Written before any change, after reading `cli.py`, `report.py`, `parsing.py`
and the tests.

## How a category reaches the report now

1. `files.read_rows` reads each row as text.
2. `parsing.to_ticket` cleans it: `clean_category` changes the web form's
   names (`Sign-in` to `login`).
3. `report.build_summary` keeps the tickets of the chosen status
   (`filter_by_status`), then counts them by category (`count_by_category`).
4. `cli.main` saves the summary as JSON.

`valid_records` and `rejected` come from all the tickets, before the status is
chosen. A test now shows that (`test_whole_file_counts_do_not_depend_on_the_status`).

## Steps

| Step | Change | File | Test that shows it works |
|---|---|---|---|
| 1 | Keep the tickets of the chosen categories, after the status | `report.py` (`build_summary` gets `categories`) | `test_report.py`: one, two, none, an unknown category |
| 2 | Add `--category` (repeatable) and pass it on | `cli.py` | `test_cli.py`: the command with `--category " Billing "` |
| 3 | Add the `categories` key only when the option is used | `report.py` | `test_baseline.py` still passes; a new test for the key |
| 4 | Describe the option | `README.md`, `--help` | `test_cli.py`: `--help` shows `--category` |

After each step: `python -m pytest`, `ruff check .`, `ruff format --check .`.
