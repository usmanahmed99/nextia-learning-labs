# ticket-assistant

Larkfield's ticket assistant, the project of the course *Building Reliable Applications with LLM APIs* on [Nextia Learning](https://learning.nextia-ai.com/courses/llm-apps/).

The assistant reads one support ticket and answers with the team that must handle it, whether a person must take over (`needs_human`), and a reply draft that an agent checks before sending. It never sends anything to a customer.

You need no account and no key: the **mock provider** replays answers that a real model (gpt-6-luna on Azure, `chat-small`) gave to the same requests when the course was recorded.

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
python -m assistant analyse T-80008
```

The answer is a JSON object with `team`, `needs_human` and `reply`, then one line with the model, the finish reason and the tokens.

## Test

```sh
python -m pytest
```

## Reset

If the project stops working, delete this folder and copy the snapshot again from [the labs repository](https://github.com/usmanahmed99/nextia-learning-labs/tree/main/C08/snapshots). Your `.venv` must be made again.

## Licence

Code: MIT (see `LICENSE`). Data in `data/` and the recorded answers in `recordings/`: CC0 1.0. The tickets and orders are synthetic.
