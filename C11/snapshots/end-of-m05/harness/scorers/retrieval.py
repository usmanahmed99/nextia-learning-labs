"""Ranking measures on saved search results (supplied by the RAG course; no search runs here).

For one question: `ranked` is the list of passage IDs the search returned, best first; `relevant` is
the set of passages marked as answering the question (in this course, by the RAG course's author,
then checked by a script).

- hit@k: 1 if at least one relevant passage is in the top k, else 0.
- recall@k: the share of the relevant passages that are in the top k.
- precision@k: the share of the top k that is relevant (the top k always has k places).
- reciprocal rank at k: 1 / the rank of the first relevant passage (1, 1/2, 1/3 ...), 0 if none is
  in the top k. The mean over questions is the MRR (mean reciprocal rank) at k.
Questions with no relevant passage (the documents do not answer them) are left out of every mean.
"""

import json
from pathlib import Path

from ..dataset import DATA

RANKINGS = DATA / "retrieval" / "rankings.json"


def hit_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if relevant & set(ranked[:k]) else 0.0


def recall_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(relevant & set(ranked[:k])) / len(relevant)


def precision_at(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(relevant & set(ranked[:k])) / k


def reciprocal_rank(ranked: list[str], relevant: set[str], k: int = 10) -> float:
    for rank, passage in enumerate(ranked[:k], 1):
        if passage in relevant:
            return 1 / rank
    return 0.0


def load_rankings(path: Path = RANKINGS) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(data: dict, method: str, k: int = 5, question_ids: list[str] | None = None) -> dict[str, float]:
    """The four measures for one search method, averaged over the questions that have relevant passages."""
    rows = []
    for q in data["questions"]:
        if not q["relevant"] or (question_ids and q["id"] not in question_ids):
            continue
        ranked, relevant = data["rankings"][method][q["id"]], set(q["relevant"])
        rows.append((hit_at(ranked, relevant, k), recall_at(ranked, relevant, k), precision_at(ranked, relevant, k),
                     reciprocal_rank(ranked, relevant, k)))
    n = len(rows)
    return {"questions": n, "hit": sum(r[0] for r in rows) / n, "recall": sum(r[1] for r in rows) / n,
            "precision": sum(r[2] for r in rows) / n, "mrr": sum(r[3] for r in rows) / n}
