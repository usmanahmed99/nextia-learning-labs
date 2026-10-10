# Support assistant: a practice help desk you can attack safely

This is the practice project for the AI security course. It is a small help-desk assistant for two
online shops that share one platform: **Larkfield** (a home-and-garden shop) and **Bramble Books**
(a bookshop). A support team member asks the assistant to help with a ticket. The assistant looks up
orders, reads the shop's documents, reads a file the customer attached, fetches a supplier page, and
proposes a refund, a return label or an e-mail that a person approves.

You will attack this assistant with harmless, made-up attacks and watch which defences stop them.

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
python -m support_assistant cases                 # the normal tasks
python -m support_assistant cases --attacks        # the attacks
python -m support_assistant show TASK-01           # one case in full
python -m support_assistant run TASK-01 --design secure
python -m support_assistant run ATK-01 --design start      # the weak version: the attack works
python -m support_assistant run ATK-01 --design secure     # the hardened version: it is stopped
python -m support_assistant compare ATK-09 --attacks       # one attack across all five designs
python -m support_assistant eval --design secure           # how many tasks still work
python -m support_assistant eval --attacks --design secure # how many attacks still succeed
```

## The designs

A **design** says how well the assistant is defended:

Some designs (filter, controls, secure) appear as you work through the course; at the start only `start` and `prompt` exist.

- `start` — the weak start: a weak prompt, broad tools, no checks in code.
- `prompt` — a strong system prompt and clear markers around untrusted text.
- `filter` — the prompt plus a model that screens the input for an attack.
- `controls` — the checks in code: who may use which tool, a tenant and customer scope, a file
  sandbox, a web allow-list, output checks, and approval before every change.
- `secure` — the controls and the strong prompt together.

## What is inside

- `support_assistant/identity.py` — a mock sign-in: a signed token with no tenant and no role; the
  server decides the role from its own membership table.
- `support_assistant/tools.py` — the tools and the checks that run around them.
- `support_assistant/vfs.py`, `web.py` — the file sandbox and the make-believe network.
- `support_assistant/designs.py` — the five designs.
- `support_assistant/evaluate.py` — how an attack or a task is scored.
- `data/` — the shops' data, the documents, the files and the attacks.

The numbers you see are a snapshot of one model, one prompt and one date. Models change fast; the
method is what lasts. Prompt injection is not a solved problem: treat every result as a snapshot.
