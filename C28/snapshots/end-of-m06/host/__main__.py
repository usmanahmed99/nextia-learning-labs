"""python -m host "your question"   (a minimal AI application with one MCP client)

python -m host "What is the return window?"                 mock model, local server (stdio)
python -m host "Draft a reply to T-30002" --user usr-sam --tenant larkfield
python -m host "..." --model openai                         a real model (MODEL_* settings)
python -m host "..." --http http://127.0.0.1:8000/mcp --token "$TOKEN" --tenant larkfield
--yes / --no      answer the confirmation questions without asking (for scripts)
--json            print the run as JSON
--legacy          use the older initialize handshake (protocol 2025-11-25)
"""

import argparse
import json
import sys

import anyio
from mcp import Client

from host import app
from host.models import make_model


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m host")
    p.add_argument("question")
    p.add_argument("--model", default="mock")
    p.add_argument("--user", default="usr-sam")
    p.add_argument("--tenant", default="larkfield")
    p.add_argument("--scopes", help="local server only: the scopes it gets (default: read scopes)")
    p.add_argument("--http", metavar="URL")
    p.add_argument("--token")
    p.add_argument("--legacy", action="store_true")
    answer = p.add_mutually_exclusive_group()
    answer.add_argument("--yes", action="store_true")
    answer.add_argument("--no", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    def confirm(name: str, arguments: dict) -> bool:
        print(f"[host] The assistant wants to run {name} with {json.dumps(arguments)}")
        if a.yes or a.no:
            print(f"[host] Answer given by option: {'yes' if a.yes else 'no'}")
            return a.yes
        return input("[host] Run it? [y/N] ").strip().lower() in ("y", "yes")

    def show(s: app.Step) -> None:
        if a.json:
            return
        extra = "" if s.text == "final answer" or not s.data else " " + json.dumps(s.data, ensure_ascii=False)
        print(f"[{s.who}] {s.text}{extra}", flush=True)

    async def go() -> app.Run:
        model = make_model(a.model)
        run = app.Run(a.question, printer=show)
        mode = "legacy" if a.legacy else "auto"
        if a.http:
            http, target = app.http_target(a.http, a.token or "", a.tenant)
            async with http, Client(target, mode=mode) as client:
                return await app.ask(client, model, a.question, confirm, run)
        async with Client(app.server_params(a.user, a.tenant, a.scopes), mode=mode) as client:
            return await app.ask(client, model, a.question, confirm, run)

    run = anyio.run(go)
    if a.json:
        print(
            json.dumps(
                {
                    "question": run.question,
                    "answer": run.answer,
                    "usage": run.usage,
                    "steps": [s.__dict__ for s in run.steps],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("\n" + run.answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
