"""The command line of the evaluation harness: python -m harness <command> ...

Run `python -m harness --help` for the list. Every command reads saved files only (cases, saved
outputs, recorded judgments), unless you choose a live judge in .env.
"""

import argparse
import json
import sys

from . import dataset
from .dataset import load_cases

SPLIT_HELP = "dev (default), holdout, contaminated or all"


def _cases(split: str):
    if split == "holdout":
        print("Note: the holdout set is frozen. Use it once, for the release decision.\n")
    return load_cases(split=split)


def cmd_cases(a) -> None:
    cases = load_cases(split="all")
    print(f"{len(cases)} cases, dataset version {dataset.version()}")
    for split in dataset.SPLITS:
        part = [c for c in cases if c.split == split]
        print(f"  {split:13} {len(part):4}   needs a person: {sum(c.expected.needs_human for c in part):3}   "
              f"French: {sum(c.language == 'fr' for c in part):2}")


def cmd_show(a) -> None:
    case = dataset.by_id(load_cases(split="all"))[a.case_id]
    print(f"{case.case_id} | split {case.split} | slice {case.slice} | source {case.source}"
          + (f" | tags {', '.join(case.tags)}" if case.tags else ""))
    print(f"Text: {case.text or '(empty)'}" + (f"\nAttachments: {case.attachments}" if case.attachments else ""))
    e = case.expected
    print(f"Expected: team {e.team or '(none)'} | needs_human {str(e.needs_human).lower()}"
          f"{' (' + e.rule + ')' if e.rule else ''} | next step {e.next_step}")
    print(f"Reply must: {', '.join(case.criteria.must) or '-'} | must not: {', '.join(case.criteria.must_not)}")
    print(f"Labelled by: {case.label.by}, {case.label.date}; {case.label.method}; {case.label.team_source}"
          + (f"; {case.label.changed}" if case.label.changed else ""))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m harness", description="Evaluate Larkfield's support assistant from saved outputs.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("cases", help="count the cases per split").set_defaults(fn=cmd_cases)

    s = sub.add_parser("show", help="one case and its labels")
    s.add_argument("case_id")
    s.set_defaults(fn=cmd_show)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except KeyError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
