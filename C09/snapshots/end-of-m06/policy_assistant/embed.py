"""Embedding models: turn a text into a vector of numbers, so that texts with similar meaning are close.

- LocalEmbedder: an open model that runs on your computer (sentence-transformers, CPU). The default is
  intfloat/multilingual-e5-small (MIT licence, 118 million parameters, 384 numbers per text, about
  470 MB, downloaded once into the Hugging Face cache, ~/.cache/huggingface). It was chosen over
  sentence-transformers/all-MiniLM-L6-v2 (English only, 90 MB) because Larkfield has French documents
  and French questions: see the course's recorded comparison. e5 models expect "query: " before a
  question and "passage: " before a document text.
- RecordedEmbedder("embed-small"): the vectors of OpenAI's text-embedding-3-small (1,536 numbers per
  text), recorded for the course through an Azure deployment named embed-small. No account needed.
- OpenAIEmbedder: a live hosted model, with your own key (paid per token; your text leaves your computer).

An index must be searched with the SAME model (name and revision) that built it: vectors from two
models are not comparable, even when they have the same length. store.py records the model.
"""

import hashlib
import os
from pathlib import Path

import numpy as np

from .dense import normalise

LOCAL_MODEL = "intfloat/multilingual-e5-small"
LOCAL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"   # the model's Hugging Face commit, 2026-10-09
PREFIXES = {  # (query prefix, passage prefix) that each model was trained with
    "intfloat/multilingual-e5-small": ("query: ", "passage: "),
}
RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"


class RecordingNotFound(KeyError):
    pass


def text_key(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}\x00{text}".encode("utf-8")).hexdigest()[:16]


class LocalEmbedder:
    def __init__(self, name: str = LOCAL_MODEL, revision: str | None = None):
        self.name = name
        self.revision = revision or (LOCAL_REVISION if name == LOCAL_MODEL else "main")
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # slow import: only when needed

            threads = os.environ.get("ASSISTANT_TORCH_THREADS")
            if threads:
                import torch
                torch.set_num_threads(int(threads))
            self._model = SentenceTransformer(self.name, revision=self.revision, device="cpu")
        return self._model

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def _encode(self, texts: list[str]) -> np.ndarray:
        return normalise(self.model.encode(list(texts), batch_size=16, normalize_embeddings=True))

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode([PREFIXES.get(self.name, ("", ""))[0] + t for t in texts])

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([PREFIXES.get(self.name, ("", ""))[1] + t for t in texts])


class RecordedEmbedder:
    """Replays vectors recorded from a hosted model. A text that was not recorded raises RecordingNotFound."""

    def __init__(self, name: str = "embed-small", folder: Path = RECORDINGS):
        self.name = name
        path = folder / f"embeddings_{name}.npz"
        data = np.load(path)
        self.revision = str(data["revision"])
        self.vectors = dict(zip((str(k) for k in data["keys"]), data["vectors"]))
        self.dim = int(data["vectors"].shape[1])

    def _get(self, texts: list[str]) -> np.ndarray:
        out = []
        for t in texts:
            key = text_key(self.name, t)
            if key not in self.vectors:
                raise RecordingNotFound(f"No recorded {self.name} vector for this text (key {key}): only the course's "
                                        "chunks and questions were recorded.")
            out.append(self.vectors[key])
        return normalise(np.array(out, dtype=np.float32))

    embed_queries = _get
    embed_passages = _get


class OpenAIEmbedder:
    """A live embedding model behind an OpenAI-compatible /embeddings endpoint (needs a key)."""

    def __init__(self, name: str, base_url: str, api_key: str, revision: str = "live", headers: dict | None = None):
        from openai import OpenAI

        self.name, self.revision = name, revision
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed", max_retries=2, timeout=60,
                             default_headers=headers)
        self.dim = None
        self.last_usage = 0

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), 64):
            response = self.client.embeddings.create(model=self.name, input=list(texts[i:i + 64]))
            out += [d.embedding for d in response.data]
            self.last_usage += response.usage.prompt_tokens
        vectors = normalise(np.array(out, dtype=np.float32))
        self.dim = vectors.shape[1]
        return vectors

    embed_queries = _embed
    embed_passages = _embed


def make_embedder(name: str = LOCAL_MODEL):
    """'embed-small' -> recorded vectors; any other name -> a local sentence-transformers model."""
    if name == "embed-small":
        return RecordedEmbedder(name)
    return LocalEmbedder(name)
