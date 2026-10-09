"""Command line.

    python -m assistant analyse T-80008     analyse one ticket (the provider comes from .env; default: mock)
"""

import argparse
import json
import sys

from .config import Settings, make_provider
from .context import build_request
from .data import load_ticket
from .providers import ProviderError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m assistant")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("analyse", help="analyse one ticket").add_argument("ticket_id")
    args = parser.parse_args(argv)

    try:
        ticket = load_ticket(args.ticket_id)
    except KeyError as error:
        print(error.args[0], file=sys.stderr)
        return 2
    settings = Settings.from_env()
    request = build_request(ticket, settings.model, "v1")
    try:
        completion = make_provider(settings).complete(request)
    except ProviderError as error:  # the provider failed: say so clearly, without a traceback
        print(f"No answer: {error}", file=sys.stderr)
        return 1
    try:
        print(json.dumps(json.loads(completion.text), indent=2, ensure_ascii=False))
    except (TypeError, json.JSONDecodeError):
        print(completion.text)
        print("(This answer is not valid JSON.)")
    print(f"{completion.model} | finish_reason: {completion.finish_reason} | {completion.input_tokens} tokens in, "
          f"{completion.output_tokens} out | {completion.latency_s} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
