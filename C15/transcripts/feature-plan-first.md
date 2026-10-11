# Recorded session: feature-plan-first

| | |
|---|---|
| Lesson | Break work into steps |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/cli.py`, `ticket_cleaner/report.py`, `README.md`, `tests/test_report.py`, `tests/test_cli.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 8 acceptance checks of the task brief (one per criterion; criterion 4 has two) |
| Model calls, tokens, cost | 3 calls; 14,792 tokens in, 2,069 out; US$0.0503 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · feature checks: 1 of 8 passed (failed: test_ac1_one_category, test_ac2_two_categories, test_ac3_case_and_spaces, test_ac4_categories_key, test_ac5_whole_file_counts, test_ac6_unknown_category, test_ac7_help)

## Turn 1 (ask mode: the assistant may not change files)

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


Do not change any file yet. First read the code and explain, in a few lines, how a ticket's category goes from the input file to the report. Then propose a plan in small numbered steps. For each step, say which file changes and which test shows that the step works.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with ask edit format
Git repo: .git with 24 files
Repo-map: using 4096 tokens, auto refresh
Added README.md to the chat.
Added tests/test_cli.py to the chat.
Added tests/test_report.py to the chat.
Added ticket_cleaner/cli.py to the chat.
Added ticket_cleaner/report.py to the chat.


data/tickets.csv
### Current flow

`cli.load_rows()` reads raw records using `read_rows()` (or `fetch_rows()` for remote input). `split_records()` validates and converts them into `Ticket` 
objects and rejected records. `build_summary()` selects tickets by status, then counts their `category` values and averages their priorities. Valid and rejected
totals describe the whole input.

Please add **`ticket_cleaner/files.py`, `ticket_cleaner/parsing.py`, and `ticket_cleaner/records.py` to the chat** so I can confirm how input category names are
cleaned and mapped. I won’t change these files.

### Plan

1. **Add optional category filtering to the report.**  
   Change: `ticket_cleaner/report.py`, `tests/test_report.py`.  
   Normalize supplied names with whitespace stripping and lowercase conversion, select matching categories after status filtering, and add a sorted 
`"categories"` key only when filtering is requested. Keep whole-input totals unchanged.  
   Tests: single category, multiple categories, mixed case/whitespace, unknown category, unchanged valid/rejected totals, and exact original report structure 
without categories.

2. **Expose the repeatable CLI option.**  
   Change: `ticket_cleaner/cli.py`, `tests/test_cli.py`.  
   Add `--category NAME` using `action="append"` and pass the optional list to `build_summary()`. Include descriptive help text.  
   Tests: single and repeated options, normalization, unknown category returning exit code `0`, unchanged whole-input totals, and help output.

3. **Document the option.**  
   Change: `README.md`.  
   Add an options-table entry and examples explaining repeated categories and case/whitespace handling.  
   Check: compare the documentation with the CLI behavior and help-output test.

4. **Verify the completed change.**  
   No additional file changes unless checks uncover problems.  
   Run `python -m pytest`, `ruff check .`, and `ruff format --check .`; then run the billing, `" Billing "`, and unknown-category commands and inspect their 
reports and exit codes.

Tokens: 3.8k sent, 635 received. Cost: $0.01 message, $0.01 session.

ticket_cleaner/files.py

ticket_cleaner/parsing.py

ticket_cleaner/records.py
No other files are needed; the supplied CLI, report, README, and test files are enough.

The category flow is now confirmed:
1. `read_rows()` loads the raw category value.
2. `split_records()` validates it, then `to_ticket()` calls `clean_category()`.
3. `clean_category()` strips surrounding spaces and maps aliases such as `Sign-in` to `login`. **Other names retain their capitalization**—for example, `LOGIN` 
stays uppercase.
4. `build_summary()` filters by status and counts the stored category values.

To meet the new case-insensitive filtering requirement without changing existing reports, I’ll normalize both the requested names and ticket categories **for 
comparison only**. Existing category labels and reports without `--category` will remain unchanged.

No files have been changed.

Tokens: 5.0k sent, 205 received. Cost: $0.01 message, $0.03 session.
````

**After turn 1:** 0 files changed, +0 −0 lines (no file).

Checks: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · feature checks: 1 of 8 passed (failed: test_ac1_one_category, test_ac2_two_categories, test_ac3_case_and_spaces, test_ac4_categories_key, test_ac5_whole_file_counts, test_ac6_unknown_category, test_ac7_help)

## Turn 2 (Aider runs the tests after each edit)

### Prompt

````text
Do step 1 of your plan only, with its test. Then stop.
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
Restored previous conversation history.

Step 1 adds optional category filtering to `build_summary()`, normalizing names only for comparison and preserving reports without a filter. The report tests 
cover status/category selection, multiple names, normalization, unknown categories, and unchanged whole-file totals. No CLI or documentation changes are 
included.

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
    """Return the report, optionally selecting categories within the given status."""
    selected = filter_by_status(tickets, status)
    chosen_categories = None
    if categories is not None:
        chosen_categories = sorted({category.strip().lower() for category in categories})
        selected = [
            ticket
            for ticket in selected
            if ticket.category.strip().lower() in chosen_categories
        ]
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

tests/test_report.py
````python
<<<<<<< SEARCH
from ticket_cleaner.records import Ticket
=======
from ticket_cleaner.records import Rejected, Ticket
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
    ("status", "categories", "selected", "by_category", "average", "chosen"),
    [
        ("open", ["billing"], 1, {"billing": 1}, 1.0, ["billing"]),
        ("closed", ["billing"], 1, {"billing": 1}, 2.0, ["billing"]),
        ("open", [" Billing "], 1, {"billing": 1}, 1.0, ["billing"]),
        (
            "open",
            ["login", "billing", " BILLING "],
            2,
            {"billing": 1, "login": 1},
            1.0,
            ["billing", "login"],
        ),
        ("open", ["unknown"], 0, {}, None, ["unknown"]),
    ],
)
def test_summary_filters_categories(
    tickets, status, categories, selected, by_category, average, chosen
):
    summary = build_summary(tickets, [], status=status, categories=categories)
    assert summary["selected"] == selected
    assert summary["by_category"] == by_category
    assert summary["average_priority"] == average
    assert summary["categories"] == chosen
    assert summary["valid_records"] == len(tickets)
    assert summary["rejected"] == []


def test_category_comparison_preserves_stored_labels():
    tickets = [
        Ticket(id="T-1", status="open", category="Billing", priority=3),
    ]
    summary = build_summary(tickets, [], status="open", categories=[" billing "])
    assert summary["selected"] == 1
    assert summary["by_category"] == {"Billing": 1}
    assert summary["average_priority"] == 3.0
    assert summary["categories"] == ["billing"]


@pytest.mark.parametrize("categories", [["billing"], ["unknown"]])
def test_category_filter_preserves_whole_file_totals(tickets, categories):
    rejected = [Rejected(row=4, problems=["invalid priority"])]
    original = build_summary(tickets, rejected, status="open")
    filtered = build_summary(tickets, rejected, status="open", categories=categories)
    assert filtered["valid_records"] == original["valid_records"] == 3
    assert filtered["rejected"] == original["rejected"] == [
        {"row": 4, "problems": ["invalid priority"]}
    ]
>>>>>>> REPLACE
````

Tokens: 6.0k sent, 1.2k received. Cost: $0.02 message, $0.02 session.
Applied edit to tests/test_report.py
Applied edit to ticket_cleaner/report.py
.................................                                                                                                                        [100%]
33 passed in 0.03s
````

**After turn 2:** 2 files changed, +82 −4 lines (tests/test_report.py, ticket_cleaner/report.py).

Checks: tests: 33 passed in 0.03s · ruff check: pass · ruff format --check: 2 files would be reformatted, 13 files already formatted · feature checks: 1 of 8 passed (failed: test_ac1_one_category, test_ac2_two_categories, test_ac3_case_and_spaces, test_ac4_categories_key, test_ac5_whole_file_counts, test_ac6_unknown_category, test_ac7_help)

## The whole diff of the session

```diff
diff --git a/tests/test_report.py b/tests/test_report.py
index 2d329fb..7f9163a 100644
--- a/tests/test_report.py
+++ b/tests/test_report.py
@@ -1,6 +1,6 @@
 import pytest
 
-from ticket_cleaner.records import Ticket
+from ticket_cleaner.records import Rejected, Ticket
 from ticket_cleaner.report import average_priority, build_summary, count_by_category
 
 
@@ -30,3 +30,65 @@ def test_summary_for_a_status_with_no_tickets(tickets):
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
+    ("status", "categories", "selected", "by_category", "average", "chosen"),
+    [
+        ("open", ["billing"], 1, {"billing": 1}, 1.0, ["billing"]),
+        ("closed", ["billing"], 1, {"billing": 1}, 2.0, ["billing"]),
+        ("open", [" Billing "], 1, {"billing": 1}, 1.0, ["billing"]),
+        (
+            "open",
+            ["login", "billing", " BILLING "],
+            2,
+            {"billing": 1, "login": 1},
+            1.0,
+            ["billing", "login"],
+        ),
+        ("open", ["unknown"], 0, {}, None, ["unknown"]),
+    ],
+)
+def test_summary_filters_categories(
+    tickets, status, categories, selected, by_category, average, chosen
+):
+    summary = build_summary(tickets, [], status=status, categories=categories)
+    assert summary["selected"] == selected
+    assert summary["by_category"] == by_category
+    assert summary["average_priority"] == average
+    assert summary["categories"] == chosen
+    assert summary["valid_records"] == len(tickets)
+    assert summary["rejected"] == []
+
+
+def test_category_comparison_preserves_stored_labels():
+    tickets = [
+        Ticket(id="T-1", status="open", category="Billing", priority=3),
+    ]
+    summary = build_summary(tickets, [], status="open", categories=[" billing "])
+    assert summary["selected"] == 1
+    assert summary["by_category"] == {"Billing": 1}
+    assert summary["average_priority"] == 3.0
+    assert summary["categories"] == ["billing"]
+
+
+@pytest.mark.parametrize("categories", [["billing"], ["unknown"]])
+def test_category_filter_preserves_whole_file_totals(tickets, categories):
+    rejected = [Rejected(row=4, problems=["invalid priority"])]
+    original = build_summary(tickets, rejected, status="open")
+    filtered = build_summary(tickets, rejected, status="open", categories=categories)
+    assert filtered["valid_records"] == original["valid_records"] == 3
+    assert filtered["rejected"] == original["rejected"] == [
+        {"row": 4, "problems": ["invalid priority"]}
+    ]
diff --git a/ticket_cleaner/report.py b/ticket_cleaner/report.py
index 72456fa..7793b8e 100644
--- a/ticket_cleaner/report.py
+++ b/ticket_cleaner/report.py
@@ -21,10 +21,23 @@ def average_priority(tickets: list[Ticket]) -> float | None:
     return round(sum(ticket.priority for ticket in tickets) / len(tickets), 1)
 
 
-def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str) -> dict:
-    """Return the report as a dictionary that can be saved as JSON."""
+def build_summary(
+    tickets: list[Ticket],
+    rejected: list[Rejected],
+    status: str,
+    categories: list[str] | None = None,
+) -> dict:
+    """Return the report, optionally selecting categories within the given status."""
     selected = filter_by_status(tickets, status)
-    return {
+    chosen_categories = None
+    if categories is not None:
+        chosen_categories = sorted({category.strip().lower() for category in categories})
+        selected = [
+            ticket
+            for ticket in selected
+            if ticket.category.strip().lower() in chosen_categories
+        ]
+    summary = {
         "status": status,
         "valid_records": len(tickets),
         "selected": len(selected),
@@ -32,3 +45,6 @@ def build_summary(tickets: list[Ticket], rejected: list[Rejected], status: str)
         "average_priority": average_priority(selected),
         "rejected": [{"row": r.row, "problems": r.problems} for r in rejected],
     }
+    if chosen_categories is not None:
+        summary["categories"] = chosen_categories
+    return summary
```
