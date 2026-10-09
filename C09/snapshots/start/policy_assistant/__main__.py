"""The command line of the policy assistant.

    python -m policy_assistant inventory                    the documents, their versions, owners and access labels
    python -m policy_assistant questions [--kind KIND]      Grace's question set
"""

import argparse
import json
import sys

from .documents import PROJECT, load_inventory


def short(text: str, n: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def cmd_inventory(args) -> None:
    docs = load_inventory()
    print(f"{'document':34} {'v':>2} {'from':10} {'to':10} {'access':6} {'lang':4} {'type':9} {'format':6} owner")
    for d in docs:
        print(f"{d.doc_id:34} {d.version:>2} {d.effective_from:10} {d.effective_to or '-':10} {d.access:6} "
              f"{d.language:4} {d.doc_type:9} {d.format:6} {d.owner}")
    print(f"{len(docs)} documents: {sum(d.access == 'staff' for d in docs)} staff-only, "
          f"{sum(d.language == 'fr' for d in docs)} in French, {sum(d.format != 'md' for d in docs)} not Markdown")


def cmd_questions(args) -> None:
    lines = (PROJECT / "questions" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    qs = [json.loads(line) for line in lines if line.strip()]
    qs = [q for q in qs if not args.kind or q["kind"] == args.kind]
    for q in qs:
        print(f"{q['id']} {q['kind']:15} {q['language']} {q['as_of']}  {short(q['question'], 80)}")
    print(f"{len(qs)} questions")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m policy_assistant", description="Larkfield's policy assistant")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    s = sub.add_parser("questions"); s.add_argument("--kind")
    args = p.parse_args(argv)
    {"inventory": cmd_inventory, "questions": cmd_questions}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
