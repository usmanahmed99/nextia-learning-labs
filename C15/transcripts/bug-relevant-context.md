# Recorded session: bug-relevant-context

| | |
|---|---|
| Lesson | Supply relevant context |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/parsing.py`, `ticket_cleaner/records.py`, `tests/test_parsing.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 5 checks of Grace's bug (her export, capital letters, the web form's names, two reports of the sample file) |
| Model calls, tokens, cost | 1 calls; 4,570 tokens in, 348 out; US$0.0126 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 1 (Aider runs the tests after each edit)

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

The categories are cleaned in ticket_cleaner/parsing.py (clean_category, to_ticket); the web form's names are in ticket_cleaner/records.py (CATEGORY_ALIASES). Fix the cause, add a regression test to tests/test_parsing.py, and change nothing else.
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
Added ticket_cleaner/records.py to the chat.


data/tickets.csv

data/web-form-export.csv
`clean_category()` lowercases alias lookups but preserves case for other categories. Use `clean_text()` before resolving aliases so every category is 
normalized. Add a regression test for mixed-case categories and surrounding spaces; no other files need changes.

ticket_cleaner/parsing.py
```python
<<<<<<< SEARCH
def clean_category(value: object) -> str:
    """Return the category, with the web form's names changed to the report's names."""
    text = str(value).strip()
    return CATEGORY_ALIASES.get(text.lower(), text)
=======
def clean_category(value: object) -> str:
    """Return the normalized category, resolving the web form's aliases."""
    text = clean_text(value)
    return CATEGORY_ALIASES.get(text, text)
>>>>>>> REPLACE
```

tests/test_parsing.py
```python
<<<<<<< SEARCH
@pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
def test_web_form_names_become_report_categories(valid_raw, name):
=======
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("login", "login"),
        ("Login", "login"),
        ("LOGIN", "login"),
        (" LOGIN ", "login"),
        ("Billing ", "billing"),
        ("SHIPPING", "shipping"),
        (" Account ", "account"),
    ],
)
def test_category_case_and_spaces_are_normalized(valid_raw, name, expected):
    valid_raw["category"] = name
    assert to_ticket(valid_raw).category == expected


@pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
def test_web_form_names_become_report_categories(valid_raw, name):
>>>>>>> REPLACE
```

Tokens: 4.6k sent, 348 received. Cost: $0.01 message, $0.01 session.
Applied edit to ticket_cleaner/parsing.py
Applied edit to tests/test_parsing.py
...............................                                                                                                                          [100%]
31 passed in 0.03s
````

**After turn 1:** 2 files changed, +20 −3 lines (tests/test_parsing.py, ticket_cleaner/parsing.py).

Checks: tests: 31 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 5 of 5 passed

## The whole diff of the session

```diff
diff --git a/tests/test_parsing.py b/tests/test_parsing.py
index c2237c6..d932ca2 100644
--- a/tests/test_parsing.py
+++ b/tests/test_parsing.py
@@ -20,6 +20,23 @@ def test_text_is_cleaned(valid_raw):
     assert to_ticket(valid_raw) == expected
 
 
+@pytest.mark.parametrize(
+    ("name", "expected"),
+    [
+        ("login", "login"),
+        ("Login", "login"),
+        ("LOGIN", "login"),
+        (" LOGIN ", "login"),
+        ("Billing ", "billing"),
+        ("SHIPPING", "shipping"),
+        (" Account ", "account"),
+    ],
+)
+def test_category_case_and_spaces_are_normalized(valid_raw, name, expected):
+    valid_raw["category"] = name
+    assert to_ticket(valid_raw).category == expected
+
+
 @pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
 def test_web_form_names_become_report_categories(valid_raw, name):
     valid_raw["category"] = name
diff --git a/ticket_cleaner/parsing.py b/ticket_cleaner/parsing.py
index 41c18ce..f8f3d35 100644
--- a/ticket_cleaner/parsing.py
+++ b/ticket_cleaner/parsing.py
@@ -16,9 +16,9 @@ def clean_text(value: object) -> str:
 
 
 def clean_category(value: object) -> str:
-    """Return the category, with the web form's names changed to the report's names."""
-    text = str(value).strip()
-    return CATEGORY_ALIASES.get(text.lower(), text)
+    """Return the normalized category, resolving the web form's aliases."""
+    text = clean_text(value)
+    return CATEGORY_ALIASES.get(text, text)
 
 
 def find_problems(raw: dict) -> list[str]:
```
