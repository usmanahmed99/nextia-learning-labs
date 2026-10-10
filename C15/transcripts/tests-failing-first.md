# Recorded session: tests-failing-first

| | |
|---|---|
| Lesson | Choose meaningful checks |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/parsing.py`, `tests/test_parsing.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 5 checks of Grace's bug (her export, capital letters, the web form's names, two reports of the sample file) |
| Model calls, tokens, cost | 1 calls; 4,367 tokens in, 174 out; US$0.0105 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 1

### Prompt

````text
From: Grace (support lead)
To: Amira
Subject: login appears three times in the report

Hi Amira,

I ran the report on this week's export from the new web form:

    python -m ticket_cleaner data/web-form-export.csv

The report has three login lines and two billing lines:

    "by_category": {
      "Billing": 1,
      "LOGIN": 1,
      "Login": 1,
      "account": 1,
      "billing": 2,
      "login": 2,
      "shipping": 2
    }

They are the same teams. Before the web form, the report had one line per
team. I expected login 4, billing 3, shipping 2 and account 1. The export is
attached (data/web-form-export.csv).

Grace

A minimal input that shows the bug (two rows, same team):

    id,status,category,priority,subject
    T-1,open,login,1,One
    T-2,open,LOGIN,1,Two

`python -m ticket_cleaner minimal.csv` gives "by_category": {"LOGIN": 1, "login": 1}.
Expected: {"login": 2}. With data/tickets.csv and --status pending, the report has "LOGIN": 1;
in the Python course it had "login": 1.

Write one test in tests/test_parsing.py that fails on the current code because of this bug, and passes when the bug is fixed. Do not change ticket_cleaner/.
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


data/tickets.csv

data/web-form-export.csv
Add one regression test verifying that uppercase category names with surrounding whitespace normalize to lowercase. This fails on the current code; no changes 
to `ticket_cleaner/` are needed.

tests/test_parsing.py
```python
<<<<<<< SEARCH
def test_missing_field_is_a_problem(valid_raw):
=======
def test_category_case_and_whitespace_are_normalized(valid_raw):
    valid_raw["category"] = " LOGIN "
    assert to_ticket(valid_raw).category == "login"


def test_missing_field_is_a_problem(valid_raw):
>>>>>>> REPLACE
```

Tokens: 4.4k sent, 174 received. Cost: $0.01 message, $0.01 session.
Applied edit to tests/test_parsing.py
````

**After turn 1:** 1 files changed, +5 −0 lines (tests/test_parsing.py).

Checks: tests: 1 failed, 24 passed in 0.04s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## The whole diff of the session

```diff
diff --git a/tests/test_parsing.py b/tests/test_parsing.py
index c2237c6..b5ba5ba 100644
--- a/tests/test_parsing.py
+++ b/tests/test_parsing.py
@@ -32,6 +32,11 @@ def test_priority_outside_1_to_3_is_a_problem(valid_raw, priority):
     assert find_problems(valid_raw) == [f"priority must be 1, 2 or 3, not {priority!r}"]
 
 
+def test_category_case_and_whitespace_are_normalized(valid_raw):
+    valid_raw["category"] = " LOGIN "
+    assert to_ticket(valid_raw).category == "login"
+
+
 def test_missing_field_is_a_problem(valid_raw):
     del valid_raw["category"]
     assert find_problems(valid_raw) == ["missing category"]
```
