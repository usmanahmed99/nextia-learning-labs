# Snapshots: support-assistant at the start and at the end of each module

Each folder here is the `support-assistant` project of [AI Security, Privacy and Responsible Design](https://learning.nextia-ai.com/courses/ai-security/). `start` is the project you download in Module 1. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module you finished last and continue.

The assistant starts weak on purpose and is hardened module by module. A **design** is a set of switches (see `support_assistant/designs.py`); each module turns on more controls, and new designs appear as you learn them.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The two shops' data, the recorded model decisions, the five tools, two designs (`start`, `prompt`), the mock sign-in and the membership check, and the scoring. The assistant is weak on purpose. | 10 |
| [`end-of-m01`](end-of-m01) | Module 2 | Nothing new in code: Module 1 maps the system and measures the weak baseline with the attacks and `eval`. | 10 |
| [`end-of-m02`](end-of-m02) | Module 3 | Constrain the consequences of a mistake in code: approval before a write, role limits, least privilege, an output check that holds a leaking answer; and a model-based input filter. New designs: `filter`, `controls`, `secure`. | 16 |
| [`end-of-m03`](end-of-m03) | Module 4 | Secure the tools and their access: validated arguments, reads scoped to the shop and the ticket's customer, a file sandbox, and a web allow-list with SSRF protection. | 24 |
| [`end-of-m04`](end-of-m04) | Module 5 | The privacy inventory: where one customer's data lives, and which copies a delete cannot reach (`inventory.py`, the `inventory` command). | 27 |
| [`end-of-m05`](end-of-m05) | Module 6 | Review design and slice testing; no new code (the review uses the approval already built). | 27 |
| [`end-of-m06`](end-of-m06) | The final assignment | The security evaluation set over the whole project, replayed from the recordings; the full README. The course-end project. | 29 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live model.
- The virtual environment `.venv` and the folder `work/` (your practice database, the signing keys and saved runs). They are made again when you set up and run a command.

## Use a snapshot

1. Copy the snapshot folder somewhere outside this repository.
2. Make a virtual environment and install the requirements:

   ```sh
   python -m venv .venv
   . .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m pytest
   ```
3. Try the commands in the project `README.md`.

You need no account and no key. Every model decision is replayed from a recording; a live model (a free local one, or your own key) is optional.
