# Recorded session: bug-fix-evidence

| | |
|---|---|
| Lesson | Ask for evidence |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files given to the assistant | `ticket_cleaner/parsing.py`, `ticket_cleaner/records.py`, `tests/test_parsing.py` |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only where a turn says so; every question from Aider answered yes |
| Project | `ticket-cleaner`, the `start` snapshot, in a new Git repository |
| Checks run after each turn | `python -m pytest`, ruff, and the 5 checks of Grace's bug (her export, capital letters, the web form's names, two reports of the sample file) |
| Model calls, tokens, cost | 3 calls; 11,446 tokens in, 471 out; US$0.0276 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/ticket-cleaner`.

Before the session: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 1 (ask mode: the assistant may not change files)

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

Do not change any file yet. Give one hypothesis for the cause, with the line of code, and say which small test would show that the hypothesis is right.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with ask edit format
Git repo: .git with 24 files
Repo-map: using 4096 tokens, auto refresh
Added tests/test_parsing.py to the chat.
Added ticket_cleaner/parsing.py to the chat.
Added ticket_cleaner/records.py to the chat.


data/tickets.csv

data/web-form-export.csv
**Hypothesis:** `clean_category()` preserves the original casing for categories that are not aliases:

```python
return CATEGORY_ALIASES.get(text.lower(), text)
```

The lookup uses lowercase, but its fallback is `text`. Since `"LOGIN"` is not an alias key, it stays `"LOGIN"` instead of becoming `"login"`, splitting the 
report counts.

**Small test:** Add this regression test to `tests/test_parsing.py`:

```python
def test_category_is_lowercased(valid_raw):
    valid_raw["category"] = "LOGIN"
    assert to_ticket(valid_raw).category == "login"
```

With the current code, it fails because the actual category is `"LOGIN"`, confirming the hypothesis. No files have been changed.

Tokens: 2.8k sent, 157 received. Cost: $0.0071 message, $0.0071 session.
````

**After turn 1:** 0 files changed, +0 −0 lines (no file).

Checks: tests: 24 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 2

### Prompt

````text
Add that test to tests/test_parsing.py and nothing else. It must fail on the current code.
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
Restored previous conversation history.

Add the regression test only. It will fail on the current code because `"LOGIN"` remains uppercase.

tests/test_parsing.py
```python
<<<<<<< SEARCH
@pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
=======
def test_category_is_lowercased(valid_raw):
    valid_raw["category"] = "LOGIN"
    assert to_ticket(valid_raw).category == "login"


@pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
>>>>>>> REPLACE
```

Tokens: 4.2k sent, 112 received. Cost: $0.0096 message, $0.0096 session.
Applied edit to tests/test_parsing.py
````

**After turn 2:** 1 files changed, +5 −0 lines (tests/test_parsing.py).

Checks: tests: 1 failed, 24 passed in 0.04s · ruff check: pass · ruff format --check: pass · defect checks: 2 of 5 passed (failed: test_grace_export_one_line_per_team, test_capital_letters_do_not_matter, test_pending_report_of_the_python_course_file)

## Turn 3 (Aider runs the tests after each edit)

### Prompt

````text
Now fix the cause with the smallest change, so that all the tests pass.
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
Restored previous conversation history.

Lowercase the fallback category so non-alias names merge regardless of casing. Alias handling stays unchanged.

ticket_cleaner/parsing.py
```python
<<<<<<< SEARCH
    return CATEGORY_ALIASES.get(text.lower(), text)
=======
    return CATEGORY_ALIASES.get(text.lower(), text.lower())
>>>>>>> REPLACE
```

Tokens: 4.4k sent, 202 received. Cost: $0.01 message, $0.01 session.
Applied edit to ticket_cleaner/parsing.py
.........................                                                                                                                                [100%]
25 passed in 0.03s
````

**After turn 3:** 2 files changed, +6 −1 lines (tests/test_parsing.py, ticket_cleaner/parsing.py).

Checks: tests: 25 passed in 0.03s · ruff check: pass · ruff format --check: pass · defect checks: 5 of 5 passed

## The whole diff of the session

```diff
diff --git a/tests/test_parsing.py b/tests/test_parsing.py
index c2237c6..9131802 100644
--- a/tests/test_parsing.py
+++ b/tests/test_parsing.py
@@ -20,6 +20,11 @@ def test_text_is_cleaned(valid_raw):
     assert to_ticket(valid_raw) == expected
 
 
+def test_category_is_lowercased(valid_raw):
+    valid_raw["category"] = "LOGIN"
+    assert to_ticket(valid_raw).category == "login"
+
+
 @pytest.mark.parametrize("name", ["Sign-in", "log-in", " sign-in "])
 def test_web_form_names_become_report_categories(valid_raw, name):
     valid_raw["category"] = name
diff --git a/ticket_cleaner/parsing.py b/ticket_cleaner/parsing.py
index 41c18ce..1821416 100644
--- a/ticket_cleaner/parsing.py
+++ b/ticket_cleaner/parsing.py
@@ -18,7 +18,7 @@ def clean_text(value: object) -> str:
 def clean_category(value: object) -> str:
     """Return the category, with the web form's names changed to the report's names."""
     text = str(value).strip()
-    return CATEGORY_ALIASES.get(text.lower(), text)
+    return CATEGORY_ALIASES.get(text.lower(), text.lower())
 
 
 def find_problems(raw: dict) -> list[str]:
```
