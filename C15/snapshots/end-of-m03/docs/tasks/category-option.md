# Task: add a --category option to the report

Request: Grace (support lead) wants the report for one category, or a few.

Observed now: `python -m ticket_cleaner data/tickets.csv` always counts every
category of the chosen status.

Expected: `python -m ticket_cleaner data/tickets.csv --category billing` counts
only the billing tickets of the chosen status.

## Acceptance criteria

1. With `--category NAME`, "selected", "by_category" and "average_priority"
   count only the tickets that have the chosen status and that category.
2. `--category` can be given more than once. A ticket in any of the given
   categories counts.
3. Capital letters and spaces around the name do not matter:
   `--category " Billing "` selects the billing tickets.
4. With `--category`, the report has one more key, "categories": the chosen
   names, in small letters, sorted. Without `--category`, the report is exactly
   the same as today.
5. "valid_records" and "rejected" do not change with `--category`: they
   describe the whole file.
6. A category that no ticket has is not an error: "selected" is 0, and the
   exit code is 0.
7. `--help` and the options table in README.md describe the option.

## Constraints

- Change only ticket_cleaner/cli.py, ticket_cleaner/report.py, README.md and
  the tests.
- No new dependency.
- Keep the style: `ruff check .` and `ruff format --check .` pass.

## Evidence of done

- `python -m pytest` passes, with new tests for criteria 1 to 6.
- `ruff check .` and `ruff format --check .` pass.
- The commands in criteria 1, 3 and 6 give the results above.
