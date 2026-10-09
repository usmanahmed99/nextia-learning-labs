"""Command line.

    python -m assistant analyse T-80008 --prompt v2    analyse one ticket with prompt v1 or v2
    python -m assistant eval --prompt v1               all 69 tickets of the evaluation set, scored
"""

import argparse
import json
import sys

from .config import Settings, make_provider
from .context import build_request
from .data import load_ticket, load_tickets
from .evaluate import Row, misses, score
from .providers import Completion, ProviderError


def parse_answer(completion: Completion) -> tuple[dict | None, str]:
    """The model was asked for JSON. Return (the answer, "") or (None, why there is no answer)."""
    try:
        answer = json.loads(completion.text or "")
    except json.JSONDecodeError:
        return None, "not JSON"
    return (answer, "") if isinstance(answer, dict) else (None, "not a JSON object")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m assistant")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("analyse", help="analyse one ticket")
    one.add_argument("ticket_id")
    many = commands.add_parser("eval", help="analyse every ticket of the evaluation set and score it")
    for command in (one, many):
        command.add_argument("--prompt", default="v2", choices=["v1", "v2"])
        command.add_argument("--model", help="overrides ASSISTANT_MODEL")
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    model = args.model or settings.model
    provider = make_provider(settings)

    if args.command == "analyse":
        try:
            ticket = load_ticket(args.ticket_id)
        except KeyError as error:
            print(error.args[0], file=sys.stderr)
            return 2
        try:
            completion = provider.complete(build_request(ticket, model, args.prompt))
        except ProviderError as error:
            print(f"No answer: {error}", file=sys.stderr)
            return 1
        answer, problem = parse_answer(completion)
        print(json.dumps(answer, indent=2, ensure_ascii=False) if answer else f"{completion.text}\n({problem})")
        print(f"{completion.model} | prompt {args.prompt} | finish_reason: {completion.finish_reason} | "
              f"{completion.input_tokens} tokens in, {completion.output_tokens} out | {completion.latency_s} s")
        return 0

    rows = []
    for ticket in load_tickets().values():
        try:
            completion = provider.complete(build_request(ticket, model, args.prompt))
        except ProviderError as error:
            rows.append(Row(ticket, None, type(error).__name__))
            continue
        answer, problem = parse_answer(completion)
        rows.append(Row(ticket, answer, problem))
    print(json.dumps(score(rows), indent=2))
    print("\n".join(misses(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
