"""Hybrid search: combine keyword and vector rankings with reciprocal rank fusion (RRF).

The scores of BM25 and cosine similarity are on different scales and cannot be added. RRF uses only
the ranks: an item gets 1 / (K + rank) from every list it appears in, and the sums are sorted.
K = 60 (the value of the original paper, Cormack, Clarke and Buettcher, 2009) keeps one list's top
item from dominating. An item that both lists rank well comes first.

Worked example (K = 60): chunk A is 1st by keywords and 3rd by vectors: 1/61 + 1/63 = 0.0323.
Chunk B is 2nd by vectors only: 1/62 = 0.0161. A comes first.
"""

from .lexical import Hit

K = 60


def rrf(rankings: list[list[Hit]], k: int = 5, constant: int = K) -> list[Hit]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for hit in ranking:
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (constant + hit.rank)
    order = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [Hit(i, round(s, 6), rank) for rank, (i, s) in enumerate(order[:k], 1)]
