"""Vector search with NumPy: compare the question's vector with every chunk's vector (brute force).

The vectors are normalised to length 1, so the dot product of two vectors is their cosine similarity:
1 = same direction (same meaning, for the model), 0 = unrelated. With a few hundred chunks, comparing
with every chunk takes well under a millisecond; a vector index (for example sqlite-vec, FAISS) only
pays off with many thousands of chunks.
"""

from typing import Callable

import numpy as np

from .lexical import Hit


def normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a, b = normalise(a), normalise(b)
    return float(a @ b)


def search(query_vector: np.ndarray, matrix: np.ndarray, ids: list[str], k: int = 5,
           allowed: Callable[[str], bool] | None = None) -> list[Hit]:
    """The k chunks whose vectors are most similar to the query vector."""
    scores = normalise(matrix) @ normalise(query_vector)
    order = sorted(range(len(ids)), key=lambda i: (-scores[i], ids[i]))
    hits = [(ids[i], float(scores[i])) for i in order if allowed is None or allowed(ids[i])]
    return [Hit(i, round(s, 4), rank) for rank, (i, s) in enumerate(hits[:k], 1)]
