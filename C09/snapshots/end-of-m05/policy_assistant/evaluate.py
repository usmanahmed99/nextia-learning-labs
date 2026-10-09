"""Measure retrieval and answers against Grace's question set.

Relevance is decided per passage: a question lists its relevant passages (document, version, section).
A retrieved chunk is relevant when it comes from one of those passages (same document and version, and
it covers that section). This works for every chunker: a fixed-size chunk that spans two sections is
relevant if one of them is a relevant passage.

Retrieval measures, for one question and the top k chunks (unanswerable questions have no relevant
passage and are left out of these measures):
- hit@k:       1 if at least one of the top k chunks is relevant, else 0 (the module 1 "answerability" check).
- recall@k:    the share of the relevant passages that at least one top-k chunk covers.
- precision@k: the share of the top k chunks that are relevant.
- MRR:         1 / the rank of the first relevant chunk (0 if none in the list), averaged over questions.
Only passages that the audience may see count: for a public assistant, a staff-only passage is not
"missed" (it must not be found), and finding one is counted as a leak.
"""

import json
import re
import statistics
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
QUESTIONS = PROJECT / "questions" / "questions.jsonl"


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    language: str
    kind: str
    as_of: str
    public_ok: bool
    abstain: bool
    reference_answer: str
    keys: list
    must_not: list
    relevant: list            # [{"doc_id", "version", "section", "access"}]
    relevant_chunks: list
    wrong_version: list
    tags: list
    notes: str


def load_questions(path: Path = QUESTIONS) -> dict[str, Question]:
    qs = [Question(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {q.id: q for q in qs}


def covers(chunk, passage: dict) -> bool:
    return chunk.doc_id == passage["doc_id"] and chunk.version == passage["version"] and passage["section"] in chunk.sections


def visible(q: Question, audience: str = "staff") -> list[dict]:
    """The relevant passages that this audience may see."""
    return [p for p in q.relevant if audience == "staff" or p["access"] == "public"]


def retrieval_scores(q: Question, ranked: list, k: int, audience: str = "staff") -> dict | None:
    """Scores for one question. `ranked` is the list of retrieved chunks, best first."""
    passages = visible(q, audience)
    top = ranked[:k]
    leaks = sum(1 for c in top if audience == "public" and c.access != "public")
    wrong = sum(1 for c in top if any(covers(c, p) for p in q.wrong_version))
    if not passages:
        return {"id": q.id, "kind": q.kind, "scored": False, "leaks": leaks, "wrong_version": wrong}
    rel = [any(covers(c, p) for p in passages) for c in top]
    found = [p for p in passages if any(covers(c, p) for c in top)]
    first = next((i for i, c in enumerate(ranked) if any(covers(c, p) for p in passages)), None)
    return {
        "id": q.id, "kind": q.kind, "scored": True,
        "hit": 1.0 if any(rel) else 0.0,
        "recall": len(found) / len(passages),
        "precision": sum(rel) / k,
        "rr": 0.0 if first is None or first >= k else 1.0 / (first + 1),
        "first_rank": None if first is None else first + 1,
        "leaks": leaks, "wrong_version": wrong,
    }


def summarise(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["scored"]]
    mean = (lambda name: round(statistics.fmean(r[name] for r in scored), 3)) if scored else (lambda name: None)
    return {"questions": len(scored), "hit": mean("hit"), "recall": mean("recall"),
            "precision": mean("precision"), "mrr": mean("rr"),
            "leaks": sum(r["leaks"] for r in rows), "wrong_version": sum(r["wrong_version"] for r in rows)}


def by_kind(rows: list[dict]) -> dict:
    kinds = sorted({r["kind"] for r in rows})
    return {kind: summarise([r for r in rows if r["kind"] == kind]) for kind in kinds}


# ---------------------------------------------------------------- answers

ABSTAIN = re.compile(r"(documents?|passages?|sources?|context)\s+(do(es)?\s+not|don't|doesn't)\s+(say|answer|state|"
                     r"mention|cover|include|contain|specify)|not (stated|specified|mentioned|covered) in|"
                     r"no information|ne (le )?(disent|précisent|mentionnent|indiquent) pas|ne disent rien", re.I)


def answer_scores(q: Question, answer) -> dict:
    """Automatic checks of one answer (an Answer from answer.py, or None when there was no valid answer).

    - correct: for an answerable question, every key matches the answer text and no must_not matches;
      for an unanswerable question, the answer abstains.
    - abstained: answerable is false.
    These checks are a net with holes: a key can match a wrong sentence ("not 30 days"), and an
    honest answer can use other words. Read the misses by hand.
    """
    if answer is None:
        return {"id": q.id, "kind": q.kind, "valid": False, "correct": False, "abstained": False}
    text = answer.text()
    abstained = not answer.answerable
    if q.abstain:
        correct = abstained
    else:
        correct = (not abstained and all(re.search(k, text, re.I) for k in q.keys)
                   and not any(re.search(m, text, re.I) for m in q.must_not))
    violated = [m for m in q.must_not if re.search(m, text, re.I)]
    return {"id": q.id, "kind": q.kind, "valid": True, "correct": correct, "abstained": abstained,
            "must_not_hit": violated}
