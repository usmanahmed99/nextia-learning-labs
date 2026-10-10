# Bug: one team appears under several category names

Reported by: Grace (support lead), with this week's export from the new web
form (`data/web-form-export.csv`).

## Steps to reproduce

1. Make a file `minimal.csv` with two tickets of the same team:

   ```text
   id,status,category,priority,subject
   T-1,open,login,1,One
   T-2,open,LOGIN,1,Two
   ```

2. Run `python -m ticket_cleaner minimal.csv --output reports/minimal.json`.

## Observed

`"by_category": {"LOGIN": 1, "login": 1}`: two lines for one team.

With Grace's export, the report has `Billing`, `LOGIN` and `Login` next to
`billing` and `login`.

## Expected

`"by_category": {"login": 2}`. Capital letters and spaces around a category do
not make a new category, as for the status and the ID. With Grace's export:
account 1, billing 3, login 4, shipping 2.

## Not affected

The web form's other names (`Sign-in`, `Invoice`, `Delivery`) are already
counted under the report's names.

## Environment

The same result in a new virtual environment made from
`requirements-lock.txt` (Python 3.14), and in Grace's own environment: not an
environment problem. The rows are valid, so no warning is printed.

## Evidence of done

- A regression test with the two rows above fails on the current code and
  passes after the fix.
- Grace's export gives one line per team.
- All other tests and the sample file's report (`tests/test_baseline.py`) are
  unchanged.
