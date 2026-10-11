# Recorded session: bug-fix-blind

| | |
|---|---|
| Lesson | Ask for evidence |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/report.py`, `ticket_cleaner/cli.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 5 checks of Grace's bug (her export, capital letters, the web form's names, two reports of the sample file) |
| Model calls, tokens, cost | 2 calls; 8,779 tokens in, 863 out; US$0.0262 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 1

### Prompt

````text
Grace says the report is wrong for the new web form export. Fix it.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with diff edit format
Git repo: .git with 24 files
Repo-map: using 4096 tokens, auto refresh
Added ticket_cleaner/cli.py to the chat.
Added ticket_cleaner/report.py to the chat.

What is wrong in Grace’s report—incorrect counts, categories, priorities, or rejected rows? Please share the actual report and the expected result.

Please also add these files to the chat so I can trace how the new export is read and normalized:
- `data/web-form-export.csv`
- `ticket_cleaner/files.py`
- `ticket_cleaner/parsing.py`
- `ticket_cleaner/records.py`
- `tests/test_parsing.py`
- `tests/test_report.py`

I’ll inspect those before proposing a fix.

Tokens: 3.6k sent, 111 received. Cost: $0.0083 message, $0.0083 session.

data/web-form-export.csv

tests/test_parsing.py

tests/test_report.py

ticket_cleaner/files.py

ticket_cleaner/parsing.py

ticket_cleaner/records.py
No other files are needed. Category aliases are normalized, but ordinary categories retain their capitalization, so `Login` and `LOGIN` are counted separately 
from `login`. I’ll normalize all categories before resolving aliases and add regression tests for both parsing and the export’s report.

ticket_cleaner/parsing.py
```python
<<<<<<< SEARCH
def clean_category(value: object) -> str:
    """Return the category, with the web form's names changed to the report's names."""
    text = str(value).strip()
    return CATEGORY_ALIASES.get(text.lower(), text)
=======
def clean_category(value: object) -> str:
    """Normalize the category and map web-form aliases to report names."""
    text = clean_text(value)
    return CATEGORY_ALIASES.get(text, text)
>>>>>>> REPLACE
```

tests/test_parsing.py
```python
<<<<<<< SEARCH
@pytest.mark.parametrize("priority", ["0", "4", "high", "2.5", "-1"])
=======
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Login", "login"),
        ("LOGIN", "login"),
        ("Billing ", "billing"),
        ("Invoice", "billing"),
        ("Delivery", "shipping"),
        (" Account ", "account"),
    ],
)
def test_categories_are_normalized(valid_raw, name, expected):
    valid_raw["category"] = name
    assert to_ticket(valid_raw).category == expected


@pytest.mark.parametrize("priority", ["0", "4", "high", "2.5", "-1"])
>>>>>>> REPLACE
```

tests/test_report.py
```python
<<<<<<< SEARCH
import pytest

from ticket_cleaner.records import Ticket
=======
from pathlib import Path

import pytest

from ticket_cleaner.files import read_rows
from ticket_cleaner.parsing import split_records
from ticket_cleaner.records import Ticket
>>>>>>> REPLACE
```

tests/test_report.py
```python
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


def test_summary_for_web_form_export():
    path = Path(__file__).resolve().parents[1] / "data" / "web-form-export.csv"
    tickets, rejected = split_records(read_rows(path))

    summary = build_summary(tickets, rejected, status="open")

    assert summary == {
        "status": "open",
        "valid_records": 12,
        "selected": 10,
        "by_category": {
            "account": 1,
            "billing": 3,
            "login": 4,
            "shipping": 2,
        },
        "average_priority": 1.9,
        "rejected": [],
    }
>>>>>>> REPLACE
```

Tokens: 5.2k sent, 752 received. Cost: $0.02 message, $0.03 session.
Applied edit to ticket_cleaner/parsing.py
Applied edit to tests/test_report.py
Applied edit to tests/test_parsing.py
````

**After turn 1:** 3 files changed, +44 −3 lines (tests/test_parsing.py, tests/test_report.py, ticket_cleaner/parsing.py).

Checks: tests: 31 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 5 of 5 passed

## The whole diff of the session

```diff
diff --git a/tests/test_parsing.py b/tests/test_parsing.py
index c2237c6..b6b0c40 100644
--- a/tests/test_parsing.py
+++ b/tests/test_parsing.py
@@ -26,6 +26,22 @@ def test_web_form_names_become_report_categories(valid_raw, name):
     assert to_ticket(valid_raw).category == "login"
 
 
+@pytest.mark.parametrize(
+    ("name", "expected"),
+    [
+        ("Login", "login"),
+        ("LOGIN", "login"),
+        ("Billing ", "billing"),
+        ("Invoice", "billing"),
+        ("Delivery", "shipping"),
+        (" Account ", "account"),
+    ],
+)
+def test_categories_are_normalized(valid_raw, name, expected):
+    valid_raw["category"] = name
+    assert to_ticket(valid_raw).category == expected
+
+
 @pytest.mark.parametrize("priority", ["0", "4", "high", "2.5", "-1"])
 def test_priority_outside_1_to_3_is_a_problem(valid_raw, priority):
     valid_raw["priority"] = priority
diff --git a/tests/test_report.py b/tests/test_report.py
index 2d329fb..27c2950 100644
--- a/tests/test_report.py
+++ b/tests/test_report.py
@@ -1,5 +1,9 @@
+from pathlib import Path
+
 import pytest
 
+from ticket_cleaner.files import read_rows
+from ticket_cleaner.parsing import split_records
 from ticket_cleaner.records import Ticket
 from ticket_cleaner.report import average_priority, build_summary, count_by_category
 
@@ -30,3 +34,24 @@ def test_summary_for_a_status_with_no_tickets(tickets):
     assert summary["selected"] == 0
     assert summary["by_category"] == {}
     assert summary["average_priority"] is None
+
+
+def test_summary_for_web_form_export():
+    path = Path(__file__).resolve().parents[1] / "data" / "web-form-export.csv"
+    tickets, rejected = split_records(read_rows(path))
+
+    summary = build_summary(tickets, rejected, status="open")
+
+    assert summary == {
+        "status": "open",
+        "valid_records": 12,
+        "selected": 10,
+        "by_category": {
+            "account": 1,
+            "billing": 3,
+            "login": 4,
+            "shipping": 2,
+        },
+        "average_priority": 1.9,
+        "rejected": [],
+    }
diff --git a/ticket_cleaner/parsing.py b/ticket_cleaner/parsing.py
index 41c18ce..7a170f5 100644
--- a/ticket_cleaner/parsing.py
+++ b/ticket_cleaner/parsing.py
@@ -16,9 +16,9 @@ def clean_text(value: object) -> str:
 
 
 def clean_category(value: object) -> str:
-    """Return the category, with the web form's names changed to the report's names."""
-    text = str(value).strip()
-    return CATEGORY_ALIASES.get(text.lower(), text)
+    """Normalize the category and map web-form aliases to report names."""
+    text = clean_text(value)
+    return CATEGORY_ALIASES.get(text, text)
 
 
 def find_problems(raw: dict) -> list[str]:
```
