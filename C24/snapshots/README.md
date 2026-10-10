# Snapshots: support-assistant at the start and at the end of each module

Each folder here is the `support-assistant` project of [AI Security, Privacy and Responsible Design](https://learning.nextia-ai.com/courses/ai-security/). `start` is the project you download in Module 1. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module you finished last and continue.

The assistant starts weak on purpose. In each module you write the defences that the module teaches, so a snapshot has only the code of the modules before it. A **design** is a set of switches in `support_assistant/designs.py`; that file appears in Module 2, when you write the first defences.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1 | The two shops' data, the recorded model decisions, the five tools with no checks (a refund or an e-mail happens at once), a weak prompt, the mock sign-in and the membership check, a log that keeps the message text, full storage of every conversation, and the scoring. One design: `start`. | 10 |
| [`end-of-m01`](end-of-m01) | Module 2 | The threat model (`THREAT-MODEL.md`), the data-flow map (`DATA-FLOW.md`), the trust-boundary map (`trust_boundaries.json`) and the `boundaries` command that checks it against the code. | 13 |
| [`end-of-m02`](end-of-m02) | Module 3 | A strong prompt, markers around the ticket, a model input filter (designs `prompt`, `filter`). Approval in the database before every change (`approvals`, `approve`, `reject`, with the approver's role and limit), the shop and customer scope, e-mail only to the address on file, and an output check (designs `controls`, `secure`). | 28 |
| [`end-of-m03`](end-of-m03) | Module 4 | Strict tool contracts and the "no more than is still refundable" rule; the file sandbox, the web allow-list with SSRF protection, no write tools for a read-only member; `redact()`, the secrets loader, and an audit event for each blocked operation. | 41 |
| [`end-of-m04`](end-of-m04) | Module 5 | The privacy inventory (`inventory`), minimized storage with an end date, and `forget` for one customer (`storage.py`, `inventory --compare`, `forget`). | 48 |
| [`end-of-m05`](end-of-m05) | Module 6 | The review screen (`review`: the proposed change, its evidence and the reason), a reason for every decision, rejections logged as disagreements, and tests for the French and German tickets. | 54 |
| [`end-of-m06`](end-of-m06) | The final assignment | Repeated, saved evaluations (`eval --repeat 2 --save`), detection (`detect`), incident switches (`incident`), the residual-risk register, the incident plan, and the full README. The course-end project. | 60 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## Your numbers before Module 3

Until the end of Module 2 your code is not the code that the model decisions were recorded with. For the `controls` and `secure` designs, `run` can then print a note that a recorded decision was made for a different request. The recorded decision is replayed and checked against your code, so your controls still act. From Module 3 on, every design gives the course's numbers.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live model.
- The virtual environment `.venv` and the folder `work/` (your practice database, the file area, the signing keys and saved evaluations). They are made again when you set up and run a command.

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
