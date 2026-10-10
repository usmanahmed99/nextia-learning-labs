# resolution-workflow

The project of the course *AI Agents and Workflow Orchestration* (Nextia Learning), as it is at the end of the course. Larkfield's support-resolution workflow: it reads a help-desk ticket, looks up the order, the payments and the policy, proposes an action (a return label, a reshipment, a refund, or only a reply), **waits for a person's approval before any change**, makes the change safely, and records what happened.

You need no account and no key. The order, payment and shipping systems are a **practice database on your computer** (`work/larkfield.sqlite`, a copy of `data/larkfield.sqlite`): every write is a mock write into that file, and nothing reaches a real system. The model decisions come from recordings of real models (the mock provider) unless you choose a live model.

## The designs

| `--variant` | Who decides the steps | Model calls per ticket |
|---|---|---|
| `fixed` | Code: keyword rules, a regular expression for the order ID, Grace's rules in `rules.py`. The model only drafts the reply. | 1 |
| `router` | The model chooses one path (status, late, return, damaged…); code does the rest. | 2 |
| `agent` | The model chooses every read and when to finish (tool calling). | 2 to 4 |
| `agent_structured` | The same loop; the model answers with one JSON step per call (for models without tool calling). | 2 to 4 |
| `workers` | An investigator reads and writes a report; a resolver decides from the report only. | 3 to 5 |

Every design ends with a **proposal**. A proposal with changes waits for approval; nothing is written before that.

```text
ticket -> [design] -> proposal -> approval (a person) -> execute (operation IDs, reconcile) -> done
                         |                   |
                         +-> reply / ask     +-> rejected: a person takes the ticket
```

## Set up

```sh
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

## Commands

```sh
python -m resolver tasks                          # the 70 tasks (--slice adversarial, failure, ...)
python -m resolver show T-90103 --expected        # one ticket, and what Grace's policy expects
python -m resolver run T-90103                    # the agent (chat-small, recorded); waits for approval
python -m resolver run T-90103 --variant fixed    # the same ticket with fixed steps
python -m resolver approve T-90103-agent-chat-small-1 --as agent --name Amira
python -m resolver trace T-90103                  # the timeline of the last run of this ticket
python -m resolver changes                        # every mock write in your practice database
python -m resolver eval --variant agent           # all 70 tasks: outcome AND changes, by slice
python -m resolver compare                        # every recorded design side by side
python -m resolver reset                          # a fresh practice database (--all: also runs and memory)
```

Teaching switches (all simulated, in the mock services only): `--fault TOOL:MODE[:TIMES]` on `run` and `approve` (modes: `timeout`, `unavailable`, `denied`, `timeout_before_write`, `timeout_after_write`), `approve … --interrupt before-write|after-write` (a simulated crash; then `resume RUN_ID`), and `approve … --naive-retry` (retry a timed-out write with a new request: the duplicate refund that operation IDs prevent).

## Files

| Path | What it does |
|---|---|
| `resolver/data.py`, `data/` | The tasks, the practice database, the policy passages, the course's "today" (2026-10-09) |
| `resolver/systems.py` | The mock services over SQLite: reads (with dates computed), idempotent writes with operation IDs, `operation()` for reconciliation, simulated failures |
| `resolver/tools.py` | Tool contracts: Pydantic arguments, permissions in code, failures as results, write authorization |
| `resolver/schema.py` | The resolution and its write actions, as validated data, and the JSON schemas the model sees |
| `resolver/state.py` | `TaskState`: goal, evidence, status, plan, proposal, approval, operations, errors, usage, events |
| `resolver/loop.py` | The bounded loop: step limit, time, spending cap, repeated calls, errors; tool calling or structured steps |
| `resolver/workflow.py`, `resolver/rules.py` | The fixed workflow and the router; Grace's rules W1 to W8 in code |
| `resolver/agent.py` | The single agent and the two workers |
| `resolver/approval.py` | What the approver sees; who may approve (refund limits); the approved digest |
| `resolver/checkpoint.py` | The checkpoint store (`work/runs.sqlite`) |
| `resolver/execute.py` | Operation IDs, write-ahead, retries, reconciliation, the simulated crash |
| `resolver/evaluate.py` | Task-level scores: outcome, proposal, database changes, forbidden changes, cost, time |
| `resolver/trace.py` | The timeline of a run |
| `resolver/memory.py` | Long-term memory for a returning customer: trusted sources only, correction, deletion |
| `resolver/parallel.py` | Parallel reads and the merge rule for two workers |
| `resolver/providers.py`, `resolver/config.py` | The adapter (mock and OpenAI-compatible), settings, the usage cap |
| `resolver/prompts/` | Grace's policy and the prompts of each design |
| `recordings/` | The recorded model decisions that the mock replays |
| `tests/` | Normal runs, termination, permissions, approval, interrupt and resume, duplicates, adversarial tasks |

## How the mock replays a decision

Each recorded decision is stored with its task, design, step and repeat. If your request is exactly the recorded one, it replays silently. If it differs (you changed a prompt, or your evidence differs), the mock still replays the decision recorded for that task and step, and the run prints a note; your code then checks that decision against your state like any model decision. A task, design or model that was never recorded stops the run with `no_recording`: the ticket goes to a person, nothing crashes. `--repeat 2` and `--repeat 3` replay other recorded runs of the same ticket (the agent with chat-small was recorded three times).

## A live model (optional)

Copy `.env.example` to `.env`. With Ollama (free, local), `gemma3:4b` has no tool calling: use `--variant agent_structured`. With your own key, any provider with the OpenAI-compatible API works. The usage cap in `config.py` (8 model calls, 120 seconds, US$0.05 per task by default) stops a run that costs too much. `PYTEST_LIVE=1 python -m pytest -m live` runs one live task.

## Licence

MIT. The data in `data/` is CC0 (see `data/dataset.md`).
