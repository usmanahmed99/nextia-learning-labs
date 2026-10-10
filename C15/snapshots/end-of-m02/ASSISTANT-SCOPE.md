# What a coding assistant may do in this project

This file is for anyone who uses a coding assistant on ticket-cleaner: a chat
window, completions in an editor, or an agent that changes files and runs
commands. Give it to the assistant with each task, and check its work against it.

## Files

| Files | The assistant may |
|---|---|
| `ticket_cleaner/*.py`, `tests/*.py` | read and change them, for the task only |
| `README.md`, `DECISIONS.md`, `docs/` | read them; change them when the task changes what they say |
| `data/` | read them; never change, add or delete a data file |
| `requirements.txt`, `requirements-lock.txt`, `pyproject.toml` | read them; a change needs my review first (see "Dependencies") |
| `.env.example` | read it; never add a real value |
| `.env`, `.venv/`, `reports/`, `.git/` | never read or change them |

## Secrets

- `TICKETS_API_TOKEN` is a secret. It is only in my terminal or in `.env`, which
  is in `.gitignore`. The assistant never sees, prints, logs or writes it.
- Never paste a token, a password or a customer's personal data into a prompt.
  The sample data in `data/` is made up.

## Commands

| Command | Rule |
|---|---|
| `python -m pytest`, `ruff check .`, `ruff format --check .` | may run at any time: they only read the code |
| `python -m ticket_cleaner <file> --output <path>` | may run with a file in `data/` and an output in `reports/` or a temporary folder |
| `ruff format .` | changes files: I review the diff after it |
| `pip install`, `pip uninstall` | **never without my review**: I check the package first (see "Dependencies") |
| `git commit`, `git push`, `git checkout`, `git reset`, `rm` | **I run them myself**, after I read the diff |
| `python -m ticket_cleaner remote` | **needs my review**: it connects to a web service |

## External actions

The assistant does not send anything outside this computer: no web requests, no
uploads, no messages, no pull requests. The only command that uses the network
is `remote`, and I run it myself.

## Dependencies

Before a new package is added, I check on https://pypi.org that it exists, that
it is maintained, that its licence fits this project (MIT), and that the
project really needs it. The standard library comes first.

## Every change

- Work happens on a branch, never on `main`.
- I read the whole diff before I accept it, and I run the tests and ruff myself.
- A change that is not in the task goes into a separate task.
