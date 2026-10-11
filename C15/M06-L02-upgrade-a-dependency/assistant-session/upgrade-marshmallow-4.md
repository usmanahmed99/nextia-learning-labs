# Recorded session: upgrade marshmallow from 3.26.2 to 4.3.1

| | |
|---|---|
| Case study | Upgrade a dependency safely |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Files the assistant may change | `form_intake/schema.py`, `form_intake/cli.py` |
| Files it may only read | `tests/test_schema.py`, `tests/test_cli.py`, `requirements.txt`; it also sees a map of the repository |
| Settings | Aider edit format `diff`; default temperature; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` allowed and run by Aider after its edits (`--auto-test`); every question from Aider answered yes |
| Project | `form-intake`: the starter, then Grace's tests, then marshmallow 4.3.1 in both requirements files and installed (one Git commit each). The recording's copy did not yet have `data/time-formats.json`, `data/new-submissions.json` and `tools/compare.py`, nor their two lines in the README: the course team added them later, for the review steps. The assistant was not given them, and the patch applies the same way |
| Model calls, tokens, cost | 1 call; 4,664 tokens in, 1,529 out (of which 461 reasoning); US$0.0246 at the deployment's price per token (you pay nothing to read this transcript); 24.3 s |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/form-intake`.

**Before the session:** tests: 2 errors in 0.06s · ruff check: pass · ruff format --check: pass · `python -m form_intake --version`: `TypeError: Field.__init__() got an unexpected keyword argument 'missing'`

## Prompt

````text
We are upgrading marshmallow from 3.26.2 to 4.3.1 (a new major version). requirements.txt and requirements-lock.txt already say 4.3.1, and it is installed. Now the tests fail:

```
============================================================================ ERRORS ============================================================================
______________________________________________________________ ERROR collecting tests/test_cli.py ______________________________________________________________
tests/test_cli.py:6: in <module>
    from form_intake.cli import main
form_intake/cli.py:10: in <module>
    from form_intake.schema import check_submissions
form_intake/schema.py:37: in <module>
    class SubmissionSchema(Schema):
form_intake/schema.py:46: in SubmissionSchema
    category = fields.Str(missing="other", validate=validate.OneOf(CATEGORIES))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Field.__init__() got an unexpected keyword argument 'missing'
____________________________________________________________ ERROR collecting tests/test_schema.py _____________________________________________________________
tests/test_schema.py:5: in <module>
    from form_intake.schema import Submission, check_submissions
form_intake/schema.py:37: in <module>
    class SubmissionSchema(Schema):
form_intake/schema.py:46: in SubmissionSchema
    category = fields.Str(missing="other", validate=validate.OneOf(CATEGORIES))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: Field.__init__() got an unexpected keyword argument 'missing'
=================================================================== short test summary info ====================================================================
ERROR tests/test_cli.py - TypeError: Field.__init__() got an unexpected keyword argument 'missing'
ERROR tests/test_schema.py - TypeError: Field.__init__() got an unexpected keyword argument 'missing'
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
2 errors in 0.06s
```

Task: change form_intake/schema.py and form_intake/cli.py so that the project works with marshmallow 4.3.1.

Rules:
- Do not change the tests or the requirements files. The tests describe the behaviour that we want. The two tests of the page addresses failed with 3.26.2 on purpose: 4.3.1 should make them pass.
- Keep every other behaviour the same.
- Do not add a dependency.
- For each change, name the change in marshmallow 4 that makes it necessary.
````

## What the assistant printed

Aider's own lines are included. The last lines are the test command that Aider ran after its edits.

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with diff edit format
Git repo: .git with 14 files
Repo-map: using 4096 tokens, auto refresh
Added form_intake/cli.py to the chat.
Added form_intake/schema.py to the chat.
Added tests/test_cli.py to the chat (read-only).
Added requirements.txt to the chat (read-only).
Added tests/test_schema.py to the chat (read-only).


requirements-lock.txt
The migration needs changes to defaults, schema context, validators, datetime parsing, and version lookup. The URL field can stay unchanged: marshmallow 4.3.1 
handles the two page-address cases.

### 1. Validators must raise `ValidationError`

Marshmallow 4 no longer treats a validator returning `False` as a validation failure. Keep the previous default error message.

form_intake/schema.py
```python
<<<<<<< SEARCH
def not_blank(text: str) -> bool:
    """Return False for text that has only spaces."""
    return text.strip() != ""
=======
def not_blank(text: str) -> None:
    """Reject text that has only spaces."""
    if not text.strip():
        raise ValidationError("Invalid value.")
>>>>>>> REPLACE
```

### 2. Preserve the requirement for a time component

Marshmallow 4 uses `datetime.fromisoformat`, which also accepts date-only strings. Add a datetime field that retains the requirement for a date/time separator.

form_intake/schema.py
```python
<<<<<<< SEARCH
@dataclass(frozen=True)
class Submission:
=======
class SubmissionDateTime(fields.DateTime):
    """Require a time component as well as a date."""

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str) and "T" not in value and " " not in value:
            raise self.make_error("invalid", input=value, obj_type=self.OBJ_TYPE)
        return super()._deserialize(value, attr, data, **kwargs)


@dataclass(frozen=True)
class Submission:
>>>>>>> REPLACE
```

### 3. Replace removed schema context and remove `Meta.ordered`

Marshmallow 4 removed schema context. Store the supplied time directly on the schema instance. It also removed `Meta.ordered`; field ordering is preserved by 
default.

form_intake/schema.py
```python
<<<<<<< SEARCH
class SubmissionSchema(Schema):
    """Checks one submission. Pass the time now as context["now"]."""

    class Meta:
        unknown = EXCLUDE  # the form adds fields that we do not use
        ordered = True
=======
class SubmissionSchema(Schema):
    """Checks one submission against the supplied current time."""

    def __init__(self, *, now: datetime, **kwargs):
        super().__init__(**kwargs)
        self.now = now

    class Meta:
        unknown = EXCLUDE  # the form adds fields that we do not use
>>>>>>> REPLACE
```

### 4. Replace `missing` with `load_default`

Marshmallow 4 removed the deprecated `missing` field argument. Preserve all three defaults and use the stricter datetime field.

form_intake/schema.py
```python
<<<<<<< SEARCH
    category = fields.Str(missing="other", validate=validate.OneOf(CATEGORIES))
    priority = fields.Int(missing=2, validate=validate.Range(min=1, max=3))
    subject = fields.Str(required=True, validate=not_blank)
    submitted_at = fields.DateTime(required=True)
    page_url = fields.Url(missing=None, allow_none=True)
=======
    category = fields.Str(load_default="other", validate=validate.OneOf(CATEGORIES))
    priority = fields.Int(load_default=2, validate=validate.Range(min=1, max=3))
    subject = fields.Str(required=True, validate=not_blank)
    submitted_at = SubmissionDateTime(required=True)
    page_url = fields.Url(load_default=None, allow_none=True)
>>>>>>> REPLACE
```

### 5. Accept validator keyword arguments

Marshmallow 4 passes `data_key` to methods decorated with `@validates`. Accept keyword arguments and read the instance’s current time.

form_intake/schema.py
```python
<<<<<<< SEARCH
    @validates("submitted_at")
    def not_in_the_future(self, value: datetime) -> None:
        if value > self.context["now"]:
=======
    @validates("submitted_at")
    def not_in_the_future(self, value: datetime, **kwargs) -> None:
        if value > self.now:
>>>>>>> REPLACE
```

Update construction to match the replacement for removed schema context.

form_intake/schema.py
```python
<<<<<<< SEARCH
    schema = SubmissionSchema(context={"now": now})
=======
    schema = SubmissionSchema(now=now)
>>>>>>> REPLACE
```

### 6. Read the installed version using package metadata

Marshmallow 4 removed `marshmallow.__version__`. Use the standard library’s `importlib.metadata.version`, without adding a dependency.

form_intake/cli.py
```python
<<<<<<< SEARCH
from datetime import datetime
from pathlib import Path

import marshmallow
=======
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
>>>>>>> REPLACE
```

form_intake/cli.py
```python
<<<<<<< SEARCH
        version=f"form_intake {__version__} (marshmallow {marshmallow.__version__})",
=======
        version=f"form_intake {__version__} (marshmallow {version('marshmallow')})",
>>>>>>> REPLACE
```

Tokens: 4.7k sent, 1.5k received. Cost: $0.02 message, $0.02 session.
Applied edit to form_intake/schema.py
Applied edit to form_intake/cli.py
...............                                                                                                                                          [100%]
15 passed in 0.04s
````

## The diff (2 files, +27 −15)

The same diff is in `upgrade-marshmallow-4.patch` next to this file. Apply it with `git apply ../assistant-session/upgrade-marshmallow-4.patch` from the project folder.

```diff
diff --git a/form_intake/cli.py b/form_intake/cli.py
index 527d437..bf91234 100644
--- a/form_intake/cli.py
+++ b/form_intake/cli.py
@@ -2,10 +2,9 @@ import argparse
 import json
 from dataclasses import asdict
 from datetime import datetime
+from importlib.metadata import version
 from pathlib import Path
 
-import marshmallow
-
 from form_intake import __version__
 from form_intake.schema import check_submissions
 
@@ -25,7 +24,7 @@ def make_parser() -> argparse.ArgumentParser:
     parser.add_argument(
         "--version",
         action="version",
-        version=f"form_intake {__version__} (marshmallow {marshmallow.__version__})",
+        version=f"form_intake {__version__} (marshmallow {version('marshmallow')})",
     )
     return parser
 
diff --git a/form_intake/schema.py b/form_intake/schema.py
index 9f391b5..2c13aab 100644
--- a/form_intake/schema.py
+++ b/form_intake/schema.py
@@ -16,9 +16,19 @@ from marshmallow import (
 CATEGORIES = ["account", "billing", "login", "shipping", "other"]
 
 
-def not_blank(text: str) -> bool:
-    """Return False for text that has only spaces."""
-    return text.strip() != ""
+def not_blank(text: str) -> None:
+    """Reject text that has only spaces."""
+    if not text.strip():
+        raise ValidationError("Invalid value.")
+
+
+class SubmissionDateTime(fields.DateTime):
+    """Require a time component as well as a date."""
+
+    def _deserialize(self, value, attr, data, **kwargs):
+        if isinstance(value, str) and "T" not in value and " " not in value:
+            raise self.make_error("invalid", input=value, obj_type=self.OBJ_TYPE)
+        return super()._deserialize(value, attr, data, **kwargs)
 
 
 @dataclass(frozen=True)
@@ -35,23 +45,26 @@ class Submission:
 
 
 class SubmissionSchema(Schema):
-    """Checks one submission. Pass the time now as context["now"]."""
+    """Checks one submission against the supplied current time."""
+
+    def __init__(self, *, now: datetime, **kwargs):
+        super().__init__(**kwargs)
+        self.now = now
 
     class Meta:
         unknown = EXCLUDE  # the form adds fields that we do not use
-        ordered = True
 
     ticket_id = fields.Str(required=True, validate=validate.Regexp(r"^T-\d{4}$"))
     email = fields.Email(required=True)
-    category = fields.Str(missing="other", validate=validate.OneOf(CATEGORIES))
-    priority = fields.Int(missing=2, validate=validate.Range(min=1, max=3))
+    category = fields.Str(load_default="other", validate=validate.OneOf(CATEGORIES))
+    priority = fields.Int(load_default=2, validate=validate.Range(min=1, max=3))
     subject = fields.Str(required=True, validate=not_blank)
-    submitted_at = fields.DateTime(required=True)
-    page_url = fields.Url(missing=None, allow_none=True)
+    submitted_at = SubmissionDateTime(required=True)
+    page_url = fields.Url(load_default=None, allow_none=True)
 
     @validates("submitted_at")
-    def not_in_the_future(self, value: datetime) -> None:
-        if value > self.context["now"]:
+    def not_in_the_future(self, value: datetime, **kwargs) -> None:
+        if value > self.now:
             raise ValidationError("The time is in the future.")
 
     @post_load
@@ -61,7 +74,7 @@ class SubmissionSchema(Schema):
 
 def check_submissions(rows: list[dict], now: datetime) -> tuple[list, list]:
     """Return the accepted submissions, and the rejected ones with their problems."""
-    schema = SubmissionSchema(context={"now": now})
+    schema = SubmissionSchema(now=now)
     accepted, rejected = [], []
     for row in rows:
         try:
```

## After the session

- `python -m pytest`: 15 passed in 0.04s
- `python -W error -m pytest` (warnings as errors): 15 passed in 0.04s
- `ruff check .`: pass · `ruff format --check .`: pass
- `python -m form_intake --version`: `form_intake 1.0.0 (marshmallow 4.3.1)`
- `python -m form_intake data/submissions.json`: `12 submissions: 5 accepted, 7 rejected.`

The tests pass. That is not yet a review: the case study checks each change against the real changelog, and compares the decisions with the ones of 3.26.2.
