# ticket-assistant

Larkfield's ticket assistant, the project of the course *Building Reliable Applications with LLM APIs* on [Nextia Learning](https://learning.nextia-ai.com/courses/llm-apps/).

The assistant reads one support ticket and returns checked data: the `team` that must handle it, `needs_human` (true when a person must take over), a `reply` draft that an agent checks before sending, and, when the ticket names an order, the order's status from a read-only lookup. It never sends anything to a customer and never changes an order.

You need no account and no key. By default the **mock provider** replays answers that real models gave to the same requests when the course was recorded (gpt-6-luna as `chat-small` and gpt-6.1-sol as `chat-strong` on Azure, and Gemma 3 4B through Ollama on a Mac mini, 2026-10-08). A live provider is optional (see [Optional: a live model](#optional-a-live-model)).

## Set up (once)

You need Python 3.12 or newer. In a terminal, in this folder:

```sh
python3 -m venv .venv
source .venv/bin/activate              # Windows (PowerShell): .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Windows, use `python` where these steps say `python3`.

## Run

```sh
python -m assistant analyse T-80008            # one ticket: order lookup, schema, business rules
python -m assistant analyse T-80001            # the model asks for another customer's order: refused
python -m assistant analyse T-80008 --save     # save the result to results.sqlite, only if it is valid
python -m assistant eval --prompt v1           # the 69 tickets of the evaluation set, scored
python -m assistant eval --prompt v2 --model chat-strong
python -m assistant usage                      # tokens, time and cost of the calls in logs/usage.jsonl
python -m assistant.stream T-64704             # a recorded stream, replayed with its real timing
python -m assistant.stream T-64704 --cancel-after 20   # the agent presses Stop after 20 pieces
python -m assistant.stream T-64704 --cut-after 40      # the connection breaks after 40 pieces (simulated)
python -m assistant.raw T-80008                # the request body as JSON
```

`analyse` prints the result as JSON and one line: `valid`, `rejected` (a check stopped the answer; `problems` says which) or `failed` (no answer: `error` says why).

## Test

```sh
python -m pytest                 # the deterministic tests, with the recorded answers
python -m pytest -m live         # optional: 5 tickets on your live provider (skipped without one)
```

The tests cover a normal ticket, invalid output (real Markdown around the JSON from a local model), a refusal (constructed: no real refusal could be provoked), truncation (real), a timeout and a rate limit (simulated), a blocked tool argument (real), a repeated-call loop (constructed), and a cancelled and an interrupted stream (the interruption is simulated).

## Optional: a live model

Copy `.env.example` to `.env` and choose one option. Never commit `.env`.

- **Free, on your computer:** install [Ollama](https://ollama.com), run `ollama pull gemma3:4b` (about 3.3 GB), then set `ASSISTANT_PROVIDER=openai_compatible`, `ASSISTANT_BASE_URL=http://localhost:11434/v1` and `ASSISTANT_MODEL=gemma3:4b`. Gemma 3 4B does not support tools in Ollama: use `--no-tools`.
- **Your own key (paid per token):** a provider that offers the OpenAI-compatible Chat Completions API. Set `ASSISTANT_BASE_URL`, `ASSISTANT_MODEL` and `ASSISTANT_API_KEY`. One ticket uses about 2,000 to 4,000 input tokens and 100 to 500 output tokens: check your provider's price page.

A request that was not recorded cannot be replayed by the mock: you see `No recording for this request`. That happens when you change a prompt, the schema or the model name while the mock is on. Use a live provider for your own changes.

## What is where

| Path | What it does |
|---|---|
| `assistant/providers.py` | The adapter: `MockProvider`, `OpenAICompatibleProvider`, the errors |
| `assistant/config.py` | Settings from environment variables, `redact()` |
| `assistant/context.py`, `assistant/prompts/` | The request: prompt version, policy, the ticket marked as untrusted |
| `assistant/schema.py`, `assistant/validate.py` | The output contract and the two gates (schema, business rules) |
| `assistant/orders.py`, `assistant/tools.py`, `assistant/loop.py` | The read-only order lookup and the bounded tool loop |
| `assistant/history.py`, `assistant/stream.py` | Conversation state with a token budget; streaming |
| `assistant/retry.py`, `assistant/simulate.py`, `assistant/usage.py` | Retries with backoff and jitter; the simulated failing provider; the usage log and prices |
| `assistant/analyse.py`, `assistant/store.py`, `assistant/evaluate.py` | One ticket end to end; the results database; scoring |
| `data/` | `tickets.csv` (69 tickets with the expected answers), `orders.sqlite` (synthetic orders) |
| `recordings/` | The recorded answers that the mock replays |

## Reset

Delete `results.sqlite` and `logs/` to start again. If the project is broken, copy the snapshot of the last module you finished from [the labs repository](https://github.com/usmanahmed99/nextia-learning-labs/tree/main/C08/snapshots), and make `.venv` again.

## Tested

2026-10-09, Python 3.12, macOS (Apple silicon), with the versions in `requirements.txt`. Windows and Linux are not tested.

## Licence

Code: MIT (see `LICENSE`). Data in `data/` and the recorded answers in `recordings/`: CC0 1.0. The tickets and orders are synthetic.
