"""Reranking with a cross-encoder: read the question and each candidate chunk TOGETHER and score the pair.

An embedding model reads the question and the chunk separately (two vectors, compared afterwards). A
cross-encoder reads both at once, so it can see that "after 45 days" and "within 30 days" do not fit.
It is slower (one model run per candidate), so it rereads only the top candidates (20 by default) of a
first, fast search.

The model: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (Apache-2.0 on its model card, about 470 MB,
multilingual: it was trained on MS MARCO translated into 14 languages). The English
cross-encoder/ms-marco-MiniLM-L6-v2 (90 MB) is faster but made the French questions worse.
"""

import os

from .lexical import Hit

RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
RERANK_REVISION = "1427fd652930e4ba29e8149678df786c240d8825"   # Hugging Face commit, 2026-10-09


class Reranker:
    def __init__(self, name: str = RERANK_MODEL, revision: str | None = None):
        self.name = name
        self.revision = revision or (RERANK_REVISION if name == RERANK_MODEL else "main")
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            threads = os.environ.get("ASSISTANT_TORCH_THREADS")
            if threads:
                import torch
                torch.set_num_threads(int(threads))
            self._model = CrossEncoder(self.name, revision=self.revision, device="cpu")
        return self._model

    def rerank(self, query: str, candidates: list, k: int = 5) -> list[Hit]:
        """candidates: chunks (with .chunk_id and .text). Returns the k best by the cross-encoder's score."""
        if not candidates:
            return []
        scores = self.model.predict([(query, c.text) for c in candidates], batch_size=16)
        order = sorted(range(len(candidates)), key=lambda i: (-float(scores[i]), candidates[i].chunk_id))
        return [Hit(candidates[i].chunk_id, round(float(scores[i]), 4), rank) for rank, i in enumerate(order[:k], 1)]
