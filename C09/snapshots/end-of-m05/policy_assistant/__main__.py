"""The command line of the policy assistant.

    python -m policy_assistant inventory                    the documents, their versions, owners and access labels
    python -m policy_assistant questions [--kind KIND]      Grace's question set
    python -m policy_assistant parse FILE                   what the parser reads from a .md, .html or .pdf file
    python -m policy_assistant ingest [--chunker structure] [--embedder NAME|none]
    python -m policy_assistant chunks DOC_ID [--version V]  the chunks of a document and where they come from
    python -m policy_assistant search "QUESTION" [--method rerank] [--k 5] [--as-of DATE|none] [--audience staff] [--rewrite]
    python -m policy_assistant ask Q22 | "QUESTION" [--model chat-small] [--method rerank] [--closed-book]
    python -m policy_assistant eval [--method rerank] [--k 5] [--rewrite] [--answers --model chat-small]

The index is index.sqlite in the project folder (--index PATH for another one). Dates are YYYY-MM-DD.
Without --as-of, the course's date (2026-10-09) is used, so that your results match the lessons;
use --as-of today for real use.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from .documents import CORPUS, PROJECT, load_inventory

COURSE_DATE = "2026-10-09"
INDEX = PROJECT / "index.sqlite"


def as_of(value: str | None) -> str | None:
    if value in (None, ""):
        return COURSE_DATE
    if value == "none":
        return None
    if value == "today":
        return date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise SystemExit(f"--as-of must be YYYY-MM-DD, today or none, not {value!r}")
    return value


def language_of(text: str) -> str:
    return "fr" if re.search(r"[éèàùçêôî]|\b(le|la|les|est|une|des|pour|vous|quel|quelle)\b", text, re.I) else "en"


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

def make_embedder(name: str):
    if name == "none":
        return None
    from .embed import make_embedder as make

    return make(name)


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
    report = store.sync(CORPUS / "documents", args.chunker, make_embedder(args.embedder))
    print(report.line())
    meta = store.meta()
    print(f"index {path.name}: {len(store.documents())} documents, {len(store.chunks())} chunks | chunker {meta.get('chunker')} | "
          f"embeddings {meta.get('embedding_model', 'none')}")


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


def make_retriever(args, store):
    from .rerank import Reranker
    from .search import Retriever

    meta = store.meta()
    embedder = None
    if args.method in ("dense", "hybrid", "rerank"):
        embedder = make_embedder(args.embedder or meta.get("embedding_model") or "none")
        if embedder is None:
            raise SystemExit("This index has no embeddings. Run: python -m policy_assistant ingest")
    return Retriever(store, embedder, Reranker() if args.method == "rerank" else None)


def cmd_search(args) -> None:
    from .filters import Filters
    from .store import IndexMismatch

    store = open_store(args)
    retriever = make_retriever(args, store)
    filters = Filters(as_of=as_of(args.as_of), audience=args.audience)
    query = args.query
    if args.rewrite:
        from .rewrite import rewrite

        query = rewrite(args.query, make_provider(args))
        print(f"Rewritten query: {query}")
    try:
        results = retriever.search(query, args.method, args.k, filters)
    except IndexMismatch as e:
        raise SystemExit(str(e))
    for r in results:
        c = r.chunk
        print(f"{r.rank}. {r.score:>8.4f}  [{c.chunk_id}] {c.doc_id} v{c.version} | {short(c.section, 30)} | {c.access}")
        print(f"   {short(c.text.split(chr(10), 1)[-1], 100)}")
    print(f"{args.method}, top {args.k}, as of {filters.as_of or 'any date'}, audience {filters.audience}")


# ---------------------------------------------------------------- answers

def make_provider(args):
    from .config import Settings, make_provider as make

    return make(Settings.from_env())


def resolve_question(text: str, date_arg: str | None):
    from .evaluate import load_questions

    qs = load_questions()
    date_arg = None if date_arg == "none" else date_arg   # "none" turns the filter off, not the question's date
    if text in qs:
        q = qs[text]
        return q.question, (as_of(date_arg) if date_arg else q.as_of), q.language, q
    return text, as_of(date_arg), language_of(text), None


def cmd_ask(args) -> None:
    from .assistant import ask
    from .config import Settings

    question, when, lang, q = resolve_question(args.question, args.as_of)
    model = args.model or Settings.from_env().model
    if args.closed_book:
        from .answer import build_closed_book_request

        c = make_provider(args).complete(build_closed_book_request(question, model))
        print(f"Question: {question}\nThe model alone, without Larkfield's documents:\n{c.text}")
        print(f"{c.model} | {c.input_tokens} tokens in, {c.output_tokens} out | {c.latency_s} s")
        return
    store = open_store(args)
    retriever = make_retriever(args, store)
    use_date = args.as_of != "none"
    result = ask(question, when, retriever, make_provider(args), model, args.method, args.k,
                 args.audience, use_date_filter=use_date, language=lang)
    print(f"Question (date {when}{'' if use_date else ', no date filter'}): {question}")
    print(f"Passages: {', '.join(result.context.ids) or 'none'} ({result.context.tokens} tokens, estimated)")
    for cid, reason in result.context.dropped:
        print(f"  dropped {cid}: {reason}")
    if result.completion is not None and result.completion.note:
        print(f"Note: {result.completion.note}")
    if result.problem:
        print(f"No answer: {result.problem}")
        return
    a = result.answer
    print(f"Answer ({'answerable' if a.answerable else 'the documents do not answer'}): {a.answer}")
    for claim, check in zip(a.claims, result.checks):
        status = "ok" if check.ok else "CHECK: " + "; ".join(check.problems)
        print(f"  - {claim.text} [{', '.join(claim.chunk_ids)}] {status}{' (' + check.note + ')' if check.note else ''}")
    c = result.completion
    print(f"{c.model} | {c.input_tokens} tokens in, {c.output_tokens} out | {c.latency_s} s")


def cmd_eval(args) -> None:
    from .evaluate import answer_scores, by_kind, load_questions, retrieval_scores, summarise
    from .filters import Filters

    store = open_store(args)
    retriever = make_retriever(args, store)
    qs = list(load_questions().values())
    rows, answers = [], []
    provider = make_provider(args) if args.answers else None
    rewriter = make_provider(args) if args.rewrite else None
    for q in qs:
        filters = Filters(as_of=q.as_of, audience=args.audience)
        query = q.question
        if rewriter:
            from .rewrite import rewrite

            query = rewrite(q.question, rewriter) or q.question
        results = retriever.search(query, args.method, args.k, filters)
        rows.append(retrieval_scores(q, [r.chunk for r in results], args.k, args.audience))
        if provider:
            from .assistant import ask

            res = ask(q.question, q.as_of, retriever, provider, args.model, args.method, args.k, args.audience,
                      language=q.language)
            score = answer_scores(q, res.answer)
            score["citation_problems"] = sum(1 for c in res.checks if not c.ok)
            score["other_passages"] = bool(res.completion is not None and res.completion.note)
            score["problem"] = res.problem
            answers.append(score)
    s = summarise(rows)
    print(f"{args.method}, top {args.k}, audience {args.audience}: {s['questions']} questions with relevant passages")
    print(f"hit@{args.k} {s['hit']:.3f} | recall@{args.k} {s['recall']:.3f} | precision@{args.k} {s['precision']:.3f} | "
          f"MRR {s['mrr']:.3f} | staff passages shown to a public audience: {s['leaks']} | wrong versions: {s['wrong_version']}")
    print(f"{'kind':15} {'n':>3} {'hit':>6} {'recall':>7} {'MRR':>6}")
    for kind, k in by_kind(rows).items():
        if k["questions"]:
            print(f"{kind:15} {k['questions']:>3} {k['hit']:>6.3f} {k['recall']:>7.3f} {k['mrr']:>6.3f}")
    if answers:
        ok = [a for a in answers if a["valid"]]
        print(f"answers ({args.model}): {len(ok)} valid of {len(answers)} | correct by the automatic "
              f"checks {sum(a['correct'] for a in answers)} | abstained {sum(a['abstained'] for a in ok)} | "
              f"claims with a citation problem {sum(a['citation_problems'] for a in ok)}")
        other = [a["id"] for a in answers if a.get("other_passages")]
        if other:
            print(f"{len(other)} answers were recorded with other passages than yours and replayed anyway, so the answer "
                  f"measures describe the recorded search, not yours (use a live model to measure yours): {', '.join(other)}")
        missed = [a["id"] for a in answers if not a["correct"]]
        print(f"not correct: {', '.join(missed) or 'none'}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="python -m policy_assistant", description="Larkfield's policy assistant")
    p.add_argument("--index", default=str(INDEX), help="the index file (default index.sqlite)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    s = sub.add_parser("questions"); s.add_argument("--kind")
    s = sub.add_parser("parse"); s.add_argument("file")
    s = sub.add_parser("ingest")
    s.add_argument("--chunker", default="structure", choices=["fixed", "overlap", "structure"])
    s.add_argument("--embedder", default="intfloat/multilingual-e5-small",
                   help="a sentence-transformers model, embed-small (recorded vectors) or none")
    s = sub.add_parser("chunks"); s.add_argument("doc_id"); s.add_argument("--version")
    for name in ("search", "ask", "eval"):
        s = sub.add_parser(name)
        if name == "search":
            s.add_argument("query")
        if name == "ask":
            s.add_argument("question", help="a question ID such as Q22, or a question in quotes")
        s.add_argument("--method", default="rerank", choices=["bm25", "dense", "hybrid", "rerank"])
        s.add_argument("--k", type=int, default=5)
        s.add_argument("--audience", default="staff", choices=["staff", "public"])
        s.add_argument("--embedder", default=None, help="default: the model that built the index")
        if name in ("search", "ask"):
            s.add_argument("--as-of", default=None, help="YYYY-MM-DD, today, or none (no date filter); "
                           "for a question ID, its own date by default")
        if name in ("ask", "eval"):
            s.add_argument("--model", default=None if name == "ask" else "chat-small")
        if name in ("search", "eval"):
            s.add_argument("--rewrite", action="store_true", help="search with a model's rewrite of the question")
        if name == "ask":
            s.add_argument("--closed-book", action="store_true", help="ask the model alone, without any document")
        if name == "eval":
            s.add_argument("--answers", action="store_true", help="also ask the model (the mock replays recordings)")
    args = p.parse_args(argv)
    {"inventory": cmd_inventory, "questions": cmd_questions, "parse": cmd_parse, "ingest": cmd_ingest,
     "chunks": cmd_chunks, "search": cmd_search, "ask": cmd_ask, "eval": cmd_eval}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
