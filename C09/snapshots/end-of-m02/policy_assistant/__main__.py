"""The command line of the policy assistant.

    python -m policy_assistant inventory                    the documents, their versions, owners and access labels
    python -m policy_assistant questions [--kind KIND]      Grace's question set
    python -m policy_assistant parse FILE                   what the parser reads from a .md, .html or .pdf file
    python -m policy_assistant ingest [--chunker structure]
    python -m policy_assistant chunks DOC_ID [--version V]  the chunks of a document and where they come from
    python -m policy_assistant search "QUESTION" [--k 5]    keyword search (BM25) over the chunks
    python -m policy_assistant eval [--k 5]                 hit@k on the question set

The index is index.sqlite in the project folder (--index PATH for another one).
"""

import argparse
import sys
from pathlib import Path

from .documents import CORPUS, PROJECT, load_inventory

INDEX = PROJECT / "index.sqlite"


def short(text: str, n: int = 90) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------- inventory, questions, parse

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


def cmd_parse(args) -> None:
    from .parse import parse

    doc = parse(Path(args.file))
    print(f"{doc.format} | " + ", ".join(f"{k}={v}" for k, v in doc.meta.items()))
    for b in doc.blocks:
        where = f"p{b.page}" if b.page else "  "
        print(f"[{b.start:>5}-{b.end:<5}] {where} {b.kind:7} {short(b.section, 28):28} | {short(b.text, 70)}")


# ---------------------------------------------------------------- index

def open_store(args):
    from .store import Store

    path = Path(args.index)
    if not path.exists():
        raise SystemExit(f"No index at {path}. Run: python -m policy_assistant ingest")
    return Store(path)


def cmd_ingest(args) -> None:
    from .store import Store

    path = Path(args.index)
    store = Store(path)
    report = store.sync(CORPUS / "documents", args.chunker)
    print(report.line())
    print(f"index {path.name}: {len(store.documents())} documents, {len(store.chunks())} chunks | "
          f"chunker {store.meta().get('chunker')}")


def cmd_chunks(args) -> None:
    store = open_store(args)
    chunks = [c for c in store.chunks() if c.doc_id == args.doc_id and (not args.version or c.version == args.version)]
    if not chunks:
        raise SystemExit(f"No chunks for {args.doc_id}. Check the document ID with: python -m policy_assistant inventory")
    for c in chunks:
        pages = ",".join(map(str, c.pages)) or "-"
        print(f"{c.chunk_id} v{c.version} #{c.position} chars {c.start}-{c.end} pages {pages} | {len(c.text.split())} words | "
              f"{' / '.join(c.sections) or '(title)'}")
    print(f"{len(chunks)} chunks ({chunks[0].chunker}) from {chunks[0].source}")


def cmd_search(args) -> None:
    store = open_store(args)
    for hit in store.keywords.search(args.query, args.k):
        c = store.chunk(hit.id)
        print(f"{hit.rank}. {hit.score:>8.4f}  [{c.chunk_id}] {c.doc_id} v{c.version} | {short(c.section, 30)} | {c.access}")
        print(f"   {short(c.text.split(chr(10), 1)[-1], 100)}")
    print(f"BM25 over {len(store.chunks())} chunks ({store.meta().get('chunker')}), top {args.k}")


def cmd_eval(args) -> None:
    from .evaluate import by_kind, load_questions, retrieval_scores, summarise

    store = open_store(args)
    rows = []
    for q in load_questions().values():
        ranked = [store.chunk(h.id) for h in store.keywords.search(q.question, args.k)]
        rows.append(retrieval_scores(q, ranked, args.k))
    s = summarise(rows)
    print(f"BM25 over {store.meta().get('chunker')} chunks, top {args.k}: hit@{args.k} {s['hit']:.3f} "
          f"({s['questions']} questions with relevant passages)")
    for kind, k in by_kind(rows).items():
        if k["questions"]:
            print(f"  {kind:15} {k['questions']:>3} questions, hit@{args.k} {k['hit']:.3f}")
    print(f"missed: {', '.join(r['id'] for r in rows if r['scored'] and not r['hit'])}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m policy_assistant", description="Larkfield's policy assistant")
    p.add_argument("--index", default=str(INDEX), help="the index file (default index.sqlite)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    s = sub.add_parser("questions"); s.add_argument("--kind")
    s = sub.add_parser("parse"); s.add_argument("file")
    s = sub.add_parser("ingest")
    s.add_argument("--chunker", default="structure", choices=["fixed", "overlap", "structure"])
    s = sub.add_parser("chunks"); s.add_argument("doc_id"); s.add_argument("--version")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--k", type=int, default=5)
    s = sub.add_parser("eval"); s.add_argument("--k", type=int, default=5)
    args = p.parse_args(argv)
    {"inventory": cmd_inventory, "questions": cmd_questions, "parse": cmd_parse, "ingest": cmd_ingest,
     "chunks": cmd_chunks, "search": cmd_search, "eval": cmd_eval}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
