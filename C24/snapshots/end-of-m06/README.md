# Support assistant: a practice help desk you can attack safely

This is the practice project for the AI security course. It is a small help-desk assistant for two
online shops that share one platform: **Larkfield** (a home-and-garden shop) and **Bramble Books**
(a bookshop). A support team member asks the assistant to help with a ticket. The assistant looks up
orders, reads the shop's documents, reads a file the customer attached, fetches a supplier page, and
proposes a refund, a return label or an e-mail that a person approves.

You attack this assistant with harmless, made-up attacks and watch which defences stop them.

## Safe to run

- Everything is made up. No real customer, order, address or secret is here. The "secrets" are
  random strings that open nothing; the app checks whether the assistant ever reveals them.
- Every web address is a made-up host that only this project answers. Nothing is sent to the
  internet.
- The attacks are harmless and run only against this app on your computer. Never test a system you
  do not own or have permission to test.
- You do not need an account or a key. The assistant replays model decisions that were recorded for
  the course. A live model (a free local one, or your own key) is optional.

## Set up

```
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

## Try it

```
python -m support_assistant cases --attacks                 # the harmless attacks
python -m support_assistant show ATK-26                     # one case in full
python -m support_assistant boundaries                      # the trust-boundary map
python -m support_assistant run ATK-26 --design start       # the weak start: the attack works
python -m support_assistant run ATK-26 --design secure      # the hardened assistant: it is stopped
python -m support_assistant compare ATK-26                  # one attack across the five designs
python -m support_assistant eval --attacks --design secure  # how many attacks still succeed
python -m support_assistant eval --design secure            # how many normal tasks still work
```

A change waits for a person:

```
python -m support_assistant run TASK-05 --design secure     # proposes a return label
python -m support_assistant approvals                       # what waits for a decision
python -m support_assistant review AP-0001                  # the proposal, its evidence and reason
python -m support_assistant approve AP-0001 --as usr-grace --reason "unused, inside 30 days"
python -m support_assistant changes                         # what was really changed
```

Privacy, detection and incidents:

```
python -m support_assistant inventory C-50533               # where one customer's data lives
python -m support_assistant inventory C-50533 --compare     # full vs minimized storage, then forget
python -m support_assistant eval --attacks --design secure --repeat 2 --save
python -m support_assistant detect work/evals/<the saved file>.json
python -m support_assistant incident disable-tool fetch_url --reason "SSRF alert"
python -m support_assistant incident status
python -m support_assistant reset                           # a fresh practice database
```

`run`, the approval commands, `forget` and `incident` use your practice database in `work/`.
`eval`, `compare` and `inventory --compare` use a fresh copy of the data for every case. If `run`
prints a note that a recorded decision was made for a different request, your code or data differs
from the recording: the decision is replayed and checked against your state, so a control you added
still acts.

## The designs

A **design** is a set of switches in `support_assistant/designs.py`:

- `start`: the weak start. A weak prompt, broad tools, no checks in code, a raw log, full storage.
- `prompt`: a strong system prompt and clear markers around untrusted text.
- `filter`: the prompt plus a model that screens the input for an attack.
- `controls`: the checks in code with the weak prompt: approval before every change with role
  limits, tenant and customer scope, output checks, a file sandbox, a web allow-list with SSRF
  protection, and no write tools for a read-only member.
- `secure`: the controls and the strong prompt together.

Strict tool contracts, the refund rules, the audit event for a blocked operation and the redacted
secrets handling are not switches: they are the same in every design.

## What is inside

| File | What it does |
|---|---|
| `THREAT-MODEL.md`, `DATA-FLOW.md`, `trust_boundaries.json` | the threat model and the data-flow map |
| `RESIDUAL-RISKS.md`, `INCIDENT-PLAN.md` | what is left after the controls, and what to do in an incident |
| `support_assistant/identity.py` | a mock sign-in: a signed token with no tenant and no role; the server decides the role |
| `support_assistant/assistant.py` | one run: sign in, the tool loop, the output check, the approval queue, storage |
| `support_assistant/tools.py` | the tools, their strict contracts and the checks around them |
| `support_assistant/vfs.py`, `web.py` | the file sandbox and the make-believe network with an allow-list |
| `support_assistant/context.py`, `filter.py`, `prompts/` | the prompts, the delimiters, the output check and the input filter |
| `support_assistant/approvals.py` | approval in the database, review, decisions with reasons |
| `support_assistant/config.py` | settings, `redact()` and the secrets loader |
| `support_assistant/storage.py`, `inventory.py` | minimized storage, retention, `forget`, the privacy inventory |
| `support_assistant/detect.py`, `incident.py` | alerts from the audit log; turn a tool off, revoke a user |
| `support_assistant/evaluate.py` | how an attack or a task is scored |
| `data/` | the shops' data, the documents, the files, the fake web and the attacks |
| `recordings/` | the recorded model decisions that the mock replays |

The numbers you see are a snapshot of one model, one prompt and one date. Models change fast; the
method is what lasts. Prompt injection is not a solved problem.

Code: MIT. Data and recordings: CC0.
