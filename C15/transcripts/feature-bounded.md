# Recorded session: feature-bounded

| | |
|---|---|
| Lesson | Problem and acceptance criteria |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/cli.py`, `ticket_cleaner/report.py`, `README.md`, `tests/test_report.py`, `tests/test_cli.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 8 acceptance checks of the task brief (one per criterion; criterion 4 has two) |
| Model calls, tokens, cost | 1 calls; 5,527 tokens in, 2,061 out; US$0.0317 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · feature checks: 1 of 8 passed (failed: test_ac1_one_category, test_ac2_two_categories, test_ac3_case_and_spaces, test_ac4_categories_key, test_ac5_whole_file_counts, test_ac6_unknown_category, test_ac7_help)

## Turn 1

### Prompt

````text
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
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with diff edit format
Git repo: .git with 24 files
Repo-map: using 4096 tokens, auto refresh
Added README.md to the chat.
Added tests/test_cli.py to the chat.
Added tests/test_report.py to the chat.
Added ticket_cleaner/cli.py to the chat.
Added ticket_cleaner/report.py to the chat.


data/tickets.csv
I’ll add a repeatable category option, normalize and apply the category filter after the status filter, and keep whole-file validation totals unchanged. Tests 
will cover filtering, normalization, multiple categories, unknown categories, backward compatibility, and help text.

ticket_cleaner/cli.py
````python
<<<<<<< SEARCH
    parser.add_argument(
        "--output",
=======
    parser.add_argument(
        "--category",
        action="append",
        metavar="NAME",
        help="count only this category; repeat for more (case-insensitive)",
    )
    parser.add_argument(
        "--output",
>>>>>>> REPLACE
````

ticket_cleaner/cli.py
````python
<<<<<<< SEARCH
    summary = build_summary(tickets, rejected, args.status)
=======
    summary = build_summary(tickets, rejected, args.status, categories=args.category)
>>>>>>> REPLACE
````

ticket_cleaner/report.py
````python
<<<<<<< SEARCH
def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str) -> dict:
    """Return the report as a dictionary that can be saved as JSON."""
    selected = filter_by_status(tickets, status)
    return {
=======
def build_summary(
    tickets: list[Ticket],
    rejected: list[Rejected],
    status: str,
    categories: list[str] | None = None,
) -> dict:
    """Return the report, optionally selecting normalized category names."""
    selected = filter_by_status(tickets, status)
    chosen_categories = None
    if categories is not None:
        chosen_categories = sorted({category.strip().lower() for category in categories})
        category_names = set(chosen_categories)
        selected = [ticket for ticket in selected if ticket.category in category_names]
    summary = {
>>>>>>> REPLACE
````

ticket_cleaner/report.py
````python
<<<<<<< SEARCH
        "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
    }
=======
        "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
    }
    if chosen_categories is not None:
        summary["categories"] = chosen_categories
    return summary
>>>>>>> REPLACE
````

README.md
````markdown
<<<<<<< SEARCH
| `--status` | Which tickets to count: `open`, `pending` or `closed` | `open` |
| `--output` | Where to save the report | `reports/summary.json` |
=======
| `--status` | Which tickets to count: `open`, `pending` or `closed` | `open` |
| `--category NAME` | Count only this category; repeat for more. Case and surrounding spaces do not matter. | All categories |
| `--output` | Where to save the report | `reports/summary.json` |
>>>>>>> REPLACE
````

README.md
````markdown
<<<<<<< SEARCH
`python -m ticket_cleaner --help` shows the same list.

## Settings
=======
`python -m ticket_cleaner --help` shows the same list.

For example, `python -m ticket_cleaner data/tickets.csv --category billing`
counts only open billing tickets. `--category " Billing "` selects the same
tickets. Use `--category billing --category login` to select either category
within the chosen status.

With `--category`, the report includes `categories`: the chosen names,
lowercased, stripped of surrounding spaces, deduplicated and sorted.
Only `selected`, `by_category` and `average_priority` are filtered;
`valid_records` and `rejected` still describe the whole input.
An unknown category is allowed: `--category unknown` selects zero tickets
and exits successfully. Without `--category`, the report is unchanged.

## Settings
>>>>>>> REPLACE
````

tests/test_report.py
````python
<<<<<<< SEARCH
def test_summary_for_a_status_with_no_tickets(tickets):
    summary = build_summary(tickets, [], status="pending")
    assert summary["selected"] == 0
    assert summary["by_category"] == {}
    assert summary["average_priority"] is None
=======
def test_summary_for_a_status_with_no_tickets(tickets):
    summary = build_summary(tickets, [], status="pending")
    assert summary["selected"] == 0
    assert summary["by_category"] == {}
    assert summary["average_priority"] is None


def test_summary_without_categories_is_unchanged(tickets):
    assert build_summary(tickets, [], status="open") == {
        "status": "open",
        "valid_records": 3,
        "selected": 2,
        "by_category": {"billing": 1, "login": 1},
        "average_priority": 1.0,
        "rejected": [],
    }


@pytest.mark.parametrize(
    ("categories", "chosen", "selected", "counts", "average"),
    [
        (["billing"], ["billing"], 1, {"billing": 1}, 1.0),
        ([" Billing "], ["billing"], 1, {"billing": 1}, 1.0),
        (
            ["login", " Billing ", "billing"],
            ["billing", "login"],
            2,
            {"billing": 1, "login": 1},
            1.0,
        ),
        (["unknown"], ["unknown"], 0, {}, None),
    ],
)
def test_summary_filters_categories(
    tickets, categories, chosen, selected, counts, average
):
    summary = build_summary(tickets, [], status="open", categories=categories)
    assert summary["categories"] == chosen
    assert summary["selected"] == selected
    assert summary["by_category"] == counts
    assert summary["average_priority"] == average
    assert summary["valid_records"] == len(tickets)
    assert summary["rejected"] == []
>>>>>>> REPLACE
````

tests/test_cli.py
````python
<<<<<<< SEARCH
import json

from ticket_cleaner.cli import main
=======
import json

import pytest

from ticket_cleaner.cli import main
>>>>>>> REPLACE
````

tests/test_cli.py
````python
<<<<<<< SEARCH
def test_missing_file_gives_exit_code_1(tmp_path):
    assert main([str(tmp_path / "missing.csv")]) == 1
=======
def test_missing_file_gives_exit_code_1(tmp_path):
    assert main([str(tmp_path / "missing.csv")]) == 1


@pytest.mark.parametrize(
    ("categories", "chosen", "selected", "counts", "average"),
    [
        (["billing"], ["billing"], 2, {"billing": 2}, 2.5),
        ([" Billing "], ["billing"], 2, {"billing": 2}, 2.5),
        (
            ["login", "billing", " Billing "],
            ["billing", "login"],
            3,
            {"billing": 2, "login": 1},
            2.0,
        ),
        (["unknown"], ["unknown"], 0, {}, None),
    ],
)
def test_category_option(tmp_path, categories, chosen, selected, counts, average):
    output = tmp_path / "summary.json"
    argv = ["data/tickets.csv", "--output", str(output)]
    assert main(argv) == 0
    baseline = json.loads(output.read_text(encoding="utf-8"))
    assert "categories" not in baseline
    assert baseline["valid_records"] == 9
    assert len(baseline["rejected"]) == 6

    for category in categories:
        argv.extend(["--category", category])
    assert main(argv) == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary == {
        **baseline,
        "categories": chosen,
        "selected": selected,
        "by_category": counts,
        "average_priority": average,
    }


def test_category_option_respects_status(tmp_path):
    output = tmp_path / "closed.json"
    assert main(
        [
            "data/tickets.csv",
            "--status",
            "closed",
            "--category",
            "billing",
            "--output",
            str(output),
        ]
    ) == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["status"] == "closed"
    assert summary["categories"] == ["billing"]
    assert summary["selected"] == 0
    assert summary["by_category"] == {}
    assert summary["average_priority"] is None
    assert summary["valid_records"] == 9
    assert len(summary["rejected"]) == 6


def test_help_describes_category_option(capsys):
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    help_text = capsys.readouterr().out
    assert "--category NAME" in help_text
    assert "repeat for more" in help_text
>>>>>>> REPLACE
````

Tokens: 5.5k sent, 2.1k received. Cost: $0.03 message, $0.03 session.
Applied edit to ticket_cleaner/cli.py
Applied edit to tests/test_cli.py
Applied edit to ticket_cleaner/report.py
Applied edit to tests/test_report.py
Applied edit to README.md
````

**After turn 1:** 5 files changed, +145 −4 lines (README.md, tests/test_cli.py, tests/test_report.py, ticket_cleaner/cli.py, ticket_cleaner/report.py).

Checks: tests: 35 passed in 0.04s · ruff check: pass · ruff format --check: 2 files would be reformatted, 13 files already formatted · feature checks: 8 of 8 passed

## The whole diff of the session

```diff
diff --git a/README.md b/README.md
index a72c88d..d4d11e9 100644
--- a/README.md
+++ b/README.md
@@ -56,10 +56,23 @@ Options:
 |---|---|---|
 | `input` | A `.csv` or `.json` file, or `remote` to download the records | (required) |
 | `--status` | Which tickets to count: `open`, `pending` or `closed` | `open` |
+| `--category NAME` | Count only this category; repeat for more. Case and surrounding spaces do not matter. | All categories |
 | `--output` | Where to save the report | `reports/summary.json` |
 
 `python -m ticket_cleaner --help` shows the same list.
 
+For example, `python -m ticket_cleaner data/tickets.csv --category billing`
+counts only open billing tickets. `--category " Billing "` selects the same
+tickets. Use `--category billing --category login` to select either category
+within the chosen status.
+
+With `--category`, the report includes `categories`: the chosen names,
+lowercased, stripped of surrounding spaces, deduplicated and sorted.
+Only `selected`, `by_category` and `average_priority` are filtered;
+`valid_records` and `rejected` still describe the whole input.
+An unknown category is allowed: `--category unknown` selects zero tickets
+and exits successfully. Without `--category`, the report is unchanged.
+
 ## Settings
 
 Set these as environment variables. `.env.example` lists them.
diff --git a/tests/test_cli.py b/tests/test_cli.py
index a8d7562..b7a1377 100644
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -1,5 +1,7 @@
 import json
 
+import pytest
+
 from ticket_cleaner.cli import main
 
 
@@ -16,3 +18,72 @@ def test_report_for_pending_tickets(tmp_path):
 
 def test_missing_file_gives_exit_code_1(tmp_path):
     assert main([str(tmp_path / "missing.csv")]) == 1
+
+
+@pytest.mark.parametrize(
+    ("categories", "chosen", "selected", "counts", "average"),
+    [
+        (["billing"], ["billing"], 2, {"billing": 2}, 2.5),
+        ([" Billing "], ["billing"], 2, {"billing": 2}, 2.5),
+        (
+            ["login", "billing", " Billing "],
+            ["billing", "login"],
+            3,
+            {"billing": 2, "login": 1},
+            2.0,
+        ),
+        (["unknown"], ["unknown"], 0, {}, None),
+    ],
+)
+def test_category_option(tmp_path, categories, chosen, selected, counts, average):
+    output = tmp_path / "summary.json"
+    argv = ["data/tickets.csv", "--output", str(output)]
+    assert main(argv) == 0
+    baseline = json.loads(output.read_text(encoding="utf-8"))
+    assert "categories" not in baseline
+    assert baseline["valid_records"] == 9
+    assert len(baseline["rejected"]) == 6
+
+    for category in categories:
+        argv.extend(["--category", category])
+    assert main(argv) == 0
+    summary = json.loads(output.read_text(encoding="utf-8"))
+    assert summary == {
+        **baseline,
+        "categories": chosen,
+        "selected": selected,
+        "by_category": counts,
+        "average_priority": average,
+    }
+
+
+def test_category_option_respects_status(tmp_path):
+    output = tmp_path / "closed.json"
+    assert main(
+        [
+            "data/tickets.csv",
+            "--status",
+            "closed",
+            "--category",
+            "billing",
+            "--output",
+            str(output),
+        ]
+    ) == 0
+    summary = json.loads(output.read_text(encoding="utf-8"))
+    assert summary["status"] == "closed"
+    assert summary["categories"] == ["billing"]
+    assert summary["selected"] == 0
+    assert summary["by_category"] == {}
+    assert summary["average_priority"] is None
+    assert summary["valid_records"] == 9
+    assert len(summary["rejected"]) == 6
+
+
+def test_help_describes_category_option(capsys):
+    with pytest.raises(SystemExit) as error:
+        main(["--help"])
+    assert error.value.code == 0
+    help_text = capsys.readouterr().out
+    assert "--category NAME" in help_text
+    assert "repeat for more" in help_text
diff --git a/tests/test_report.py b/tests/test_report.py
index 2d329fb..e0fa996 100644
--- a/tests/test_report.py
+++ b/tests/test_report.py
@@ -30,3 +30,41 @@ def test_summary_for_a_status_with_no_tickets(tickets):
     assert summary["selected"] == 0
     assert summary["by_category"] == {}
     assert summary["average_priority"] is None
+
+
+def test_summary_without_categories_is_unchanged(tickets):
+    assert build_summary(tickets, [], status="open") == {
+        "status": "open",
+        "valid_records": 3,
+        "selected": 2,
+        "by_category": {"billing": 1, "login": 1},
+        "average_priority": 1.0,
+        "rejected": [],
+    }
+
+
+@pytest.mark.parametrize(
+    ("categories", "chosen", "selected", "counts", "average"),
+    [
+        (["billing"], ["billing"], 1, {"billing": 1}, 1.0),
+        ([" Billing "], ["billing"], 1, {"billing": 1}, 1.0),
+        (
+            ["login", " Billing ", "billing"],
+            ["billing", "login"],
+            2,
+            {"billing": 1, "login": 1},
+            1.0,
+        ),
+        (["unknown"], ["unknown"], 0, {}, None),
+    ],
+)
+def test_summary_filters_categories(
+    tickets, categories, chosen, selected, counts, average
+):
+    summary = build_summary(tickets, [], status="open", categories=categories)
+    assert summary["categories"] == chosen
+    assert summary["selected"] == selected
+    assert summary["by_category"] == counts
+    assert summary["average_priority"] == average
+    assert summary["valid_records"] == len(tickets)
+    assert summary["rejected"] == []
diff --git a/ticket_cleaner/cli.py b/ticket_cleaner/cli.py
index ed72943..6b37b65 100644
--- a/ticket_cleaner/cli.py
+++ b/ticket_cleaner/cli.py
@@ -28,6 +28,12 @@ def make_parser() -> argparse.ArgumentParser:
         choices=sorted(STATUSES),
         help="which tickets to count (default: open)",
     )
+    parser.add_argument(
+        "--category",
+        action="append",
+        metavar="NAME",
+        help="count only this category; repeat for more (case-insensitive)",
+    )
     parser.add_argument(
         "--output",
         type=Path,
@@ -62,7 +68,7 @@ def main(argv: list[str] | None = None) -> int:
     for record in rejected:
         logger.warning("row %d rejected: %s", record.row, "; ".join(record.problems))
 
-    summary = build_summary(tickets, rejected, args.status)
+    summary = build_summary(tickets, rejected, args.status, categories=args.category)
     write_json(summary, args.output)
     logger.info("wrote %s", args.output)
     print(f"{len(rows)} rows: {len(tickets)} valid, {len(rejected)} rejected.")
diff --git a/ticket_cleaner/report.py b/ticket_cleaner/report.py
index 72456fa..196eb80 100644
--- a/ticket_cleaner/report.py
+++ b/ticket_cleaner/report.py
@@ -21,10 +21,20 @@ def average_priority(tickets: list[Ticket]) -> float | None:
     return round(sum(ticket.priority for ticket in tickets) / len(tickets), 1)
 
 
-def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str) -> dict:
-    """Return the report as a dictionary that can be saved as JSON."""
+def build_summary(
+    tickets: list[Ticket],
+    rejected: list[Rejected],
+    status: str,
+    categories: list[str] | None = None,
+) -> dict:
+    """Return the report, optionally selecting normalized category names."""
     selected = filter_by_status(tickets, status)
-    return {
+    chosen_categories = None
+    if categories is not None:
+        chosen_categories = sorted({category.strip().lower() for category in categories})
+        category_names = set(chosen_categories)
+        selected = [ticket for ticket in selected if ticket.category in category_names]
+    summary = {
         "status": status,
         "valid_records": len(tickets),
         "selected": len(selected),
@@ -32,3 +42,6 @@ def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str)
         "average_priority": average_priority(selected),
         "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
     }
+    if chosen_categories is not None:
+        summary["categories"] = chosen_categories
+    return summary
```
