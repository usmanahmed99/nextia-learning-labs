# Recorded session: tests-mirror

| | |
|---|---|
| Lesson | Choose meaningful checks |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/parsing.py`, `tests/test_parsing.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 5 checks of Grace's bug (her export, capital letters, the web form's names, two reports of the sample file) |
| Model calls, tokens, cost | 1 calls; 3,583 tokens in, 441 out; US$0.0116 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 1

### Prompt

````text
Write tests for clean_category in ticket_cleaner/parsing.py.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with diff edit format
Git repo: .git with 24 files
Repo-map: using 4096 tokens, auto refresh
Added tests/test_parsing.py to the chat.
Added ticket_cleaner/parsing.py to the chat.

I’ll add direct tests for alias normalization, whitespace trimming, preserving unrecognized category names, and converting non-string inputs to text. No 
production changes are needed.

tests/test_parsing.py
```python
<<<<<<< SEARCH
from ticket_cleaner.parsing import find_problems, split_records, to_ticket
=======
from ticket_cleaner.parsing import (
    clean_category,
    find_problems,
    split_records,
    to_ticket,
)
>>>>>>> REPLACE
```

tests/test_parsing.py
```python
<<<<<<< SEARCH
def test_valid_record_has_no_problems(valid_raw):
    assert find_problems(valid_raw) == []
=======
@pytest.mark.parametrize("value", ["Sign-in", "log-in", " sign-in ", " LOG-IN "])
def test_clean_category_normalizes_aliases(value):
    assert clean_category(value) == "login"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("billing", "billing"),
        (" billing ", "billing"),
        (" Custom Category ", "Custom Category"),
        ("", ""),
        (" \t\n ", ""),
    ],
)
def test_clean_category_trims_text_without_changing_unrecognized_names(value, expected):
    assert clean_category(value) == expected


@pytest.mark.parametrize(("value", "expected"), [(123, "123"), (None, "None")])
def test_clean_category_converts_non_string_values_to_text(value, expected):
    assert clean_category(value) == expected


def test_valid_record_has_no_problems(valid_raw):
    assert find_problems(valid_raw) == []
>>>>>>> REPLACE
```

Tokens: 3.6k sent, 441 received. Cost: $0.01 message, $0.01 session.
Applied edit to tests/test_parsing.py
````

**After turn 1:** 1 files changed, +30 −1 lines (tests/test_parsing.py).

Checks: tests: 35 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## The whole diff of the session

```diff
diff --git a/tests/test_parsing.py b/tests/test_parsing.py
index c2237c6..b7dd218 100644
--- a/tests/test_parsing.py
+++ b/tests/test_parsing.py
@@ -1,6 +1,11 @@
 import pytest
 
-from ticket_cleaner.parsing import find_problems, split_records, to_ticket
+from ticket_cleaner.parsing import (
+    clean_category,
+    find_problems,
+    split_records,
+    to_ticket,
+)
 from ticket_cleaner.records import Ticket
 
 
@@ -9,6 +14,30 @@ def valid_raw():
     return {"id": "T-1001", "status": "open", "category": "billing", "priority": "2"}
 
 
+@pytest.mark.parametrize("value", ["Sign-in", "log-in", " sign-in ", " LOG-IN "])
+def test_clean_category_normalizes_aliases(value):
+    assert clean_category(value) == "login"
+
+
+@pytest.mark.parametrize(
+    ("value", "expected"),
+    [
+        ("billing", "billing"),
+        (" billing ", "billing"),
+        (" Custom Category ", "Custom Category"),
+        ("", ""),
+        (" \t\n ", ""),
+    ],
+)
+def test_clean_category_trims_text_without_changing_unrecognized_names(value, expected):
+    assert clean_category(value) == expected
+
+
+@pytest.mark.parametrize(("value", "expected"), [(123, "123"), (None, "None")])
+def test_clean_category_converts_non_string_values_to_text(value, expected):
+    assert clean_category(value) == expected
+
+
 def test_valid_record_has_no_problems(valid_raw):
     assert find_problems(valid_raw) == []
```
