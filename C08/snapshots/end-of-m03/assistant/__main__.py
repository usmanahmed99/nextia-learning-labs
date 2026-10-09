"""Command line.

    python -m assistant analyse T-80008            one ticket: schema and checks, prompt v2
    python -m assistant analyse T-80008 --save     ... and save it to results.sqlite if it is valid
    python -m assistant eval --prompt v1           the 69 tickets, structured output
"""

import argparse
import json
import sys

from .analyse import analyse_ticket
from .config import Settings, make_provider
from .data import load_ticket, load_tickets
from .evaluate import Row, misses, score
from .providers import ProviderError
from .store import InvalidResult, ResultStore
from .validate import Problem, Verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m assistant")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("analyse", help="analyse one ticket")
    one.add_argument("ticket_id")
    one.add_argument("--save", action="store_true", help="save a valid result to results.sqlite")
    many = commands.add_parser("eval", help="analyse every ticket of the evaluation set and score it")
    for command in (one, many):
        command.add_argument("--prompt", default="v2", choices=["v1", "v2"])
        command.add_argument("--model", help="overrides ASSISTANT_MODEL")
        command.add_argument("--no-schema", action="store_true", help="do not request structured output")
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    model = args.model or settings.model
    provider = make_provider(settings)
    options = dict(model=model, prompt=args.prompt, structured=not args.no_schema)

    if args.command == "analyse":
        try:
            ticket = load_ticket(args.ticket_id)
        except KeyError as error:
            print(error.args[0], file=sys.stderr)
            return 2
        outcome = analyse_ticket(ticket, provider, **options)
        print(json.dumps(outcome.to_dict(), indent=2, ensure_ascii=False))
        tokens_in = sum(c.input_tokens for c in outcome.completions)
        tokens_out = sum(c.output_tokens for c in outcome.completions)
        print(f"{outcome.status} | {model} | prompt {args.prompt} | {len(outcome.completions)} call(s) | "
              f"{tokens_in} tokens in, {tokens_out} out")
        if args.save:
            try:
                failed = [Problem("failed", outcome.error)] if outcome.status == "failed" else []
                verdict = Verdict(outcome.analysis, outcome.problems + failed)
                ResultStore().save(ticket.ticket_id, verdict, args.prompt, model)
                print("Saved to results.sqlite.")
            except InvalidResult as error:
                print(error, file=sys.stderr)
                return 1
        return 0 if outcome.status == "valid" else 1

    rows = []
    for ticket in load_tickets().values():
        try:
            outcome = analyse_ticket(ticket, provider, **options)
        except ProviderError as error:  # for example a request that was not recorded
            rows.append(Row(ticket, None, type(error).__name__))
            continue
        answer = outcome.analysis.model_dump() if outcome.analysis else None
        note = ", ".join(p.code for p in outcome.problems) or ("failed" if outcome.status == "failed" else "")
        rows.append(Row(ticket, answer, note))
    print(json.dumps(score(rows), indent=2))
    print("\n".join(misses(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
