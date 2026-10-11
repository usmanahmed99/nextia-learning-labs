# Recorded session: feature-chat-mode

| | |
|---|---|
| Lesson | Assistant interaction modes |
| Assistant | chat mode: a short script that sends the task and the files in one message, as you do when you paste code into a chat window (chat_mode.py) |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/cli.py`, `ticket_cleaner/report.py`, `README.md`, `tests/test_report.py`, `tests/test_cli.py` |
| Settings | one message; the reply's diff applied with `git apply` |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 8 acceptance checks of the task brief (one per criterion; criterion 4 has two) |
| Model calls, tokens, cost | 1 calls; 2,688 tokens in, 2,554 out; US$0.0309 at the deployment's price per token (you pay nothing to read this transcript) |

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
Adds repeatable, case-insensitive category filtering while preserving whole-file totals and the existing report when no category is supplied. Includes documentation and regression tests for criteria 1–6 and help text.

I can’t run pytest, Ruff, or the sample commands in this chat environment.

```diff
diff --git a/ticket_cleaner/cli.py b/ticket_cleaner/cli.py
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
+        help="count only these categories; repeatable, ignoring case and outer spaces",
+    )
     parser.add_argument(
         "--output",
         type=Path,
@@ -62,7 +68,7 @@ def main(argv: list[str] | None = None) -> int:
     for record in rejected:
         logger.warning("row %d rejected: %s", record.row, "; ".join(record.problems))
 
-    summary = build_summary(tickets, rejected, args.status)
+    summary = build_summary(tickets, rejected, args.status, args.category)
     write_json(summary, args.output)
     logger.info("wrote %s", args.output)
     print(f"{len(rows)} rows: {len(tickets)} valid, {len(rejected)} rejected.")
diff --git a/ticket_cleaner/report.py b/ticket_cleaner/report.py
--- a/ticket_cleaner/report.py
+++ b/ticket_cleaner/report.py
@@ -21,10 +21,23 @@ def average_priority(tickets: list[Ticket]) -> float | None:
     return round(sum(ticket.priority for ticket in tickets) / len(tickets), 1)
 
 
-def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str) -> dict:
+def build_summary(
+    tickets: list[Ticket],
+    rejected: list[Rejected],
+    status: str,
+    categories: list[str] | None = None,
+) -> dict:
     """Return the report as a dictionary that can be saved as JSON."""
     selected = filter_by_status(tickets, status)
-    return {
+    chosen_categories = None
+    if categories is not None:
+        chosen_categories = sorted({category.strip().lower() for category in categories})
+        selected = [
+            ticket for ticket in selected if ticket.category in chosen_categories
+        ]
+
+    summary = {
         "status": status,
         "valid_records": len(tickets),
         "selected": len(selected),
@@ -32,3 +45,6 @@ def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str) -> dict:
         "average_priority": average_priority(selected),
         "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
     }
+    if chosen_categories is not None:
+        summary["categories"] = chosen_categories
+    return summary
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -58,10 +58,19 @@ Options:
 |---|---|---|
 | `input` | A `.csv` or `.json` file, or `remote` to download the records | (required) |
 | `--status` | Which tickets to count: `open`, `pending` or `closed` | `open` |
+| `--category NAME` | Count only this category within the chosen status; repeat for several categories. Case and outer spaces do not matter. | All categories |
 | `--output` | Where to save the report | `reports/summary.json` |
 
 `python -m ticket_cleaner --help` shows the same list.
 
+For example, `python -m ticket_cleaner data/tickets.csv --category billing`
+counts only open billing tickets. Add `--category login` to include login tickets
+as well. `--category " Billing "` also selects billing.
+
+With this option, the report includes `categories`: the chosen names, lowercased,
+deduplicated and sorted. `valid_records` and `rejected` still describe the whole
+file. A category with no matching tickets produces an empty selection, not an error.
+
 ## Settings
 
 Set these as environment variables. `.env.example` lists them.
diff --git a/tests/test_report.py b/tests/test_report.py
--- a/tests/test_report.py
+++ b/tests/test_report.py
@@ -32,3 +32,41 @@ def test_summary_for_a_status_with_no_tickets(tickets):
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
+            ["login", "billing", " BILLING "],
+            ["billing", "login"],
+            3,
+            {"billing": 1, "login": 2},
+            2.3,
+        ),
+        (["unknown"], ["unknown"], 0, {}, None),
+    ],
+)
+def test_summary_filters_categories(tickets, categories, chosen, selected, counts, average):
+    tickets.append(Ticket(id="T-4", status="open", category="login", priority=5))
+    summary = build_summary(tickets, [], status="open", categories=categories)
+
+    assert summary["categories"] == chosen
+    assert summary["selected"] == selected
+    assert summary["by_category"] == counts
+    assert summary["average_priority"] == average
+    assert summary["valid_records"] == 4
+    assert summary["rejected"] == []
diff --git a/tests/test_cli.py b/tests/test_cli.py
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -1,6 +1,8 @@
 import json
 
-from ticket_cleaner.cli import main
+import pytest
+
+from ticket_cleaner.cli import main, make_parser
 
 
 def test_report_for_pending_tickets(tmp_path):
@@ -20,3 +22,65 @@ def test_report_for_pending_tickets(tmp_path):
 
 def test_missing_file_gives_exit_code_1(tmp_path):
     assert main([str(tmp_path / "missing.csv")]) == 1
+
+
+@pytest.mark.parametrize(
+    ("status", "categories", "chosen", "selected", "counts", "average"),
+    [
+        ("open", ["billing"], ["billing"], 1, {"billing": 1}, 3.0),
+        ("open", [" Billing "], ["billing"], 1, {"billing": 1}, 3.0),
+        (
+            "open",
+            ["login", "billing", " BILLING "],
+            ["billing", "login"],
+            3,
+            {"billing": 1, "login": 2},
+            3.0,
+        ),
+        ("open", ["unknown"], ["unknown"], 0, {}, None),
+        ("closed", ["billing"], ["billing"], 1, {"billing": 1}, 2.0),
+    ],
+)
+def test_category_report(tmp_path, status, categories, chosen, selected, counts, average):
+    source = tmp_path / "tickets.json"
+    source.write_text(
+        json.dumps(
+            [
+                {"id": "T-1", "status": "open", "category": "login", "priority": 1},
+                {"id": "T-2", "status": "open", "category": "billing", "priority": 3},
+                {"id": "T-3", "status": "closed", "category": "billing", "priority": 2},
+                {"id": "T-4", "status": "open", "category": "login", "priority": 5},
+                {},
+            ]
+        ),
+        encoding="utf-8",
+    )
+    output = tmp_path / "summary.json"
+    args = [str(source), "--status", status, "--output", str(output)]
+
+    assert main(args) == 0
+    baseline = json.loads(output.read_text(encoding="utf-8"))
+    assert "categories" not in baseline
+    assert baseline["valid_records"] == 4
+    assert len(baseline["rejected"]) == 1
+
+    for category in categories:
+        args.extend(["--category", category])
+    assert main(args) == 0
+    summary = json.loads(output.read_text(encoding="utf-8"))
+
+    assert summary["status"] == status
+    assert summary["categories"] == chosen
+    assert summary["selected"] == selected
+    assert summary["by_category"] == counts
+    assert summary["average_priority"] == average
+    assert summary["valid_records"] == baseline["valid_records"]
+    assert summary["rejected"] == baseline["rejected"]
+
+
+def test_help_describes_category_option():
+    help_text = make_parser().format_help()
+    assert "--category NAME" in help_text
+    assert "repeatable" in help_text
+    assert "ignoring case and outer spaces" in help_text
```
````

Applying the reply's diff: git apply: FAILED: error: corrupt patch at ~/recording/reply.diff:54

**After turn 1:** 0 files changed, +0 −0 lines (no file).

Checks: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · feature checks: 1 of 8 passed (failed: test_ac1_one_category, test_ac2_two_categories, test_ac3_case_and_spaces, test_ac4_categories_key, test_ac5_whole_file_counts, test_ac6_unknown_category, test_ac7_help)

## The whole diff of the session

```diff
(no change)
```
