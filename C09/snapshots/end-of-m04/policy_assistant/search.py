"""One entry point for every search method, with the metadata filters applied first.

    bm25    keyword search (lexical.py)
    dense   vector search (dense.py) with the embedding model that built the index
    hybrid  bm25 + dense, combined with reciprocal rank fusion (hybrid.py)
    rerank  hybrid's top CANDIDATES, reread by the cross-encoder (rerank.py)
"""

from dataclasses import dataclass

from .dense import search as dense_search
from .filters import Filters
from .hybrid import rrf
from .lexical import Hit
from .metadata import Chunk
from .store import IndexMismatch, Store

METHODS = ("bm25", "dense", "hybrid", "rerank")
CANDIDATES = 20   # how many results each first-stage method passes on to fusion and reranking


@dataclass(frozen=True)
class Result:
    chunk: Chunk
    score: float
    rank: int


class Retriever:
    def __init__(self, store: Store, embedder=None, reranker=None):
        self.store, self.embedder, self.reranker = store, embedder, reranker
        self._chunks = {c.chunk_id: c for c in store.chunks()}

    def _allowed(self, filters: Filters):
        return lambda chunk_id: filters.allows(self._chunks[chunk_id])

    def _check_model(self) -> None:
        if self.embedder is None:
            raise ValueError("Dense search needs an embedding model.")
        meta = self.store.meta()
        if (meta.get("embedding_model"), meta.get("embedding_revision")) != (self.embedder.name, self.embedder.revision):
            raise IndexMismatch(
                f"The index was built with {meta.get('embedding_model') or 'no embedding model'} "
                f"({meta.get('embedding_revision', '')}), and the question would be embedded with "
                f"{self.embedder.name} ({self.embedder.revision}). Vectors of two models are not comparable.")

    def bm25(self, query: str, k: int, filters: Filters) -> list[Hit]:
        return self.store.keywords.search(query, k, self._allowed(filters))

    def dense(self, query: str, k: int, filters: Filters) -> list[Hit]:
        self._check_model()
        ids, matrix = self.store.vectors()
        return dense_search(self.embedder.embed_queries([query])[0], matrix, ids, k, self._allowed(filters))

    def hybrid(self, query: str, k: int, filters: Filters) -> list[Hit]:
        return rrf([self.bm25(query, CANDIDATES, filters), self.dense(query, CANDIDATES, filters)], k)

    def rerank(self, query: str, k: int, filters: Filters) -> list[Hit]:
        if self.reranker is None:
            raise ValueError("Reranking needs a cross-encoder (rerank.Reranker).")
        candidates = [self._chunks[h.id] for h in self.hybrid(query, CANDIDATES, filters)]
        return self.reranker.rerank(query, candidates, k)

    def search(self, query: str, method: str = "hybrid", k: int = 5, filters: Filters = Filters()) -> list[Result]:
        if method not in METHODS:
            raise ValueError(f"Unknown method {method!r}: use one of {', '.join(METHODS)}.")
        hits = getattr(self, method)(query, k, filters)
        return [Result(self._chunks[h.id], h.score, h.rank) for h in hits]
