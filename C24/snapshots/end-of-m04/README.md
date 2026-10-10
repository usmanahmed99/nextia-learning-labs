# Support assistant: a practice help desk you can attack safely

This is the practice project for the AI security course. It is a small help-desk assistant for two
online shops that share one platform: **Larkfield** (a home-and-garden shop) and **Bramble Books**
(a bookshop). A support team member asks the assistant to help with a ticket. The assistant looks up
orders, reads the shop's documents, reads a file the customer attached, fetches a supplier page, and
can make a refund, a return label or an e-mail.

You attack this assistant with harmless, made-up attacks, and you add the defences one module at a
time. It starts weak on purpose.

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
python -m support_assistant run ATK-26 --design start       # the weak start: the attack works
python -m support_assistant eval --attacks --design start   # how many attacks succeed
python -m support_assistant eval --design start             # how many normal tasks work
python -m support_assistant changes                         # what the assistant changed
python -m support_assistant reset                           # a fresh practice database
```

Each module adds code and commands. `python -m support_assistant --help` lists the commands your
project has now.

`run` uses your practice database in `work/`; `eval` and `compare` use a fresh copy of the data for
every case. If `run` prints a note that a recorded decision was made for a different request, your
code or data differs from the recording: the decision is replayed and checked against your state.

The numbers you see are a snapshot of one model, one prompt and one date. Models change fast; the
method is what lasts. Prompt injection is not a solved problem.

Code: MIT. Data and recordings: CC0.
