# Project card: form-intake (marshmallow 3.26.2 → 4.3.1)

Used by: the case study *Upgrade a dependency safely* of *AI-Assisted Software Development*, `starter.zip` and `finished.zip`

| Field | Value |
|---|---|
| Source | Written by the Nextia Learning course team for this case study. It is not a copy of another project. |
| Publisher / creator | Nextia Learning |
| Licence | MIT (`LICENSE` in the project, "Copyright (c) Nextia Learning") |
| Attribution text | "form-intake, written for Nextia Learning's course AI-Assisted Software Development (MIT)." |
| The dependency | [marshmallow](https://pypi.org/project/marshmallow/) by Steven Loria and contributors, MIT. Not included in the zips: `pip` installs it from PyPI. |
| Versions | from `marshmallow==3.26.2` (2025-12-22, the last 3.x release on PyPI) to `marshmallow==4.3.1` (2026-08-08, the latest release) |
| The breaking change | marshmallow 4.0.0 (2025-04-16): [changelog](https://github.com/marshmallow-code/marshmallow/blob/4.3.1/CHANGELOG.rst) and [upgrading guide](https://marshmallow.readthedocs.io/en/latest/upgrading.html#upgrading-4-0) |
| The assistant session | `assistant-session/upgrade-marshmallow-4.md` and `.patch`: one real recorded session (Aider 0.86.2, Apache-2.0; an Azure-hosted model). You do not need an assistant or an account. |
| Data | `data/submissions.json` (12 submissions), `data/time-formats.json` (10), `data/new-submissions.json` (10). All invented for the course: no real person, address or ticket. |
| Size | 7 Python files in the starter (286 lines with the tests), 3 small JSON files; the venv is about 49 MB |
| Tested | macOS (Apple silicon), Python 3.14.6, pip 26.1.2. Windows and Linux commands are written, not run. |

## What one row means

One object in a data file is one submission of Larkfield's web form: a ticket ID, the customer's email address, a category, a priority from 1 to 3, a subject, the local time when it was sent, and the page where the customer pressed Help. `form-intake` accepts it, or rejects it with every problem that it has.

## Why this project

The case study needs a real, documented breaking release of a well-known package, a small project that uses the parts that break, and a reason to upgrade that a user can see. marshmallow 4.0.0 removed APIs that 3.x had marked as deprecated, and changed how times are read. Two later 4.x releases fixed web addresses that 3.26.2 rejects (4.2.4: international domain names; 4.3.1: a fragment after an empty path). The alternatives that the course team compared are in the authors' research notes: pydantic 1 → 2 (a very wide change, mostly renames that its own tool can make) and click 8.1 → 8.2 (a smaller break, mostly in the test helper, with no reason that a user can see).

## What is constructed

- The whole project, its tests and its three data files: written for the course, MIT.
- Grace's two problem submissions use made-up addresses on `larkfield.example` (a reserved example domain).
- The six time formats that the form "might" send in `data/time-formats.json` are a probe, written to pin the old behaviour. The real form sends `YYYY-MM-DDTHH:MM:SS`.

Real: marshmallow and its changelog, every command output in the case study, and the recorded assistant session.

## Limitations and cautions

- One dependency, one upgrade, one recorded session. Another run, model or assistant can propose a different change.
- The tests and the probe cover the rules in the README, not every input that a web form can send.
- `form-intake` treats times as Larkfield's local time without a zone. It is a teaching project, not a production service.
