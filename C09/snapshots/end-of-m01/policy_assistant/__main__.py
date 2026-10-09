"""The command line of the policy assistant.

    python -m policy_assistant inventory                    the documents, their versions, owners and access labels
    python -m policy_assistant questions [--kind KIND]      Grace's question set
    python -m policy_assistant search "QUESTION" [--k 5]    keyword search (BM25) over the sections of the Markdown documents
    python -m policy_assistant eval [--k 5]                 hit@k on the question set: the baseline to beat

Module 1 searches the 32 Markdown documents, one section at a time. The 4 HTML and PDF documents are
not searched yet: parsing them is Module 2.
"""

import argparse
import sqlite3
import sys

from .documents import load_inventory, sections
from .lexical import KeywordIndex


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
    from .evaluate import load_questions

    qs = [q for q in load_questions().values() if not args.kind or q.kind == args.kind]
    for q in qs:
        print(f"{q.id} {q.kind:15} {q.language} {q.as_of}  {short(q.question, 80)}")
    print(f"{len(qs)} questions")


def section_index():
    """An in-memory keyword index of every section of the Markdown documents."""
    all_sections = [s for d in load_inventory() if d.format == "md" for s in sections(d)]
    index = KeywordIndex(sqlite3.connect(":memory:"))
    index.add((s.passage_id, s.text) for s in all_sections)
    return index, {s.passage_id: s for s in all_sections}


def cmd_search(args) -> None:
    index, by_id = section_index()
    for hit in index.search(args.query, args.k):
        s = by_id[hit.id]
        print(f"{hit.rank}. {hit.score:>8.4f}  {hit.id}")
        print(f"   {short(s.text.split(chr(10), 2)[-1], 100)}")
    print(f"BM25 over {len(by_id)} sections of the Markdown documents, top {args.k}")


def cmd_eval(args) -> None:
    from .evaluate import by_kind, load_questions, retrieval_scores, summarise

    index, by_id = section_index()
    rows = []
    for q in load_questions().values():
        ranked = [by_id[h.id] for h in index.search(q.question, args.k)]
        rows.append(retrieval_scores(q, ranked, args.k))
    s = summarise(rows)
    print(f"BM25 over sections, top {args.k}: hit@{args.k} {s['hit']:.3f} ({s['questions']} questions with relevant passages)")
    for kind, k in by_kind(rows).items():
        if k["questions"]:
            print(f"  {kind:15} {k['questions']:>3} questions, hit@{args.k} {k['hit']:.3f}")
    print(f"missed: {', '.join(r['id'] for r in rows if r['scored'] and not r['hit'])}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m policy_assistant", description="Larkfield's policy assistant")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    s = sub.add_parser("questions"); s.add_argument("--kind")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--k", type=int, default=5)
    s = sub.add_parser("eval"); s.add_argument("--k", type=int, default=5)
    args = p.parse_args(argv)
    {"inventory": cmd_inventory, "questions": cmd_questions, "search": cmd_search, "eval": cmd_eval}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
