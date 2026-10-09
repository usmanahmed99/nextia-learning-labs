"""The index: one SQLite file with the documents, their chunks, the keyword index and the vectors.

Tables:
  documents  one row per document version: metadata, the file and the SHA-256 of its bytes
  chunks     one row per chunk: its text, positions, sections, pages and the document's metadata
  keyword_index (FTS5) the chunks' text for BM25 (lexical.py)
  vectors    one row per chunk: its embedding (float32 bytes)
  meta       how the index was built: chunker, embedding model and revision

`sync()` builds the index from the folder of documents. For now it rebuilds everything every time:
simple and always correct, but every document is parsed, chunked and embedded again.
The embedding model and its revision are recorded in meta: search.py refuses to search the index
with another model.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .chunk import chunk as make_chunks
from .lexical import KeywordIndex
from .metadata import Chunk
from .parse import parse

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  doc_id TEXT, version TEXT, title TEXT, file TEXT, format TEXT, content_hash TEXT,
  effective_from TEXT, effective_to TEXT, owner TEXT, access TEXT, language TEXT, doc_type TEXT,
  PRIMARY KEY (doc_id, version));
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY, doc_id TEXT, version TEXT, title TEXT, chunker TEXT, position INTEGER,
  start INTEGER, "end" INTEGER, text TEXT, sections TEXT, pages TEXT, effective_from TEXT,
  effective_to TEXT, access TEXT, language TEXT, doc_type TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS vectors (chunk_id TEXT PRIMARY KEY, vector BLOB);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""
SUFFIXES = (".md", ".html", ".pdf")


class IndexMismatch(Exception):
    """The index was built with another embedding model."""


@dataclass
class SyncReport:
    added: list = field(default_factory=list)
    chunks_added: int = 0

    def line(self) -> str:
        return f"{len(self.added)} documents, {self.chunks_added} chunks (rebuilt from scratch)"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.executescript(SCHEMA)
        self.keywords = KeywordIndex(self.conn)
        self._matrix = None

    def meta(self) -> dict:
        return dict(self.conn.execute("SELECT key, value FROM meta"))

    def set_meta(self, **values) -> None:
        self.conn.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", [(k, str(v)) for k, v in values.items()])

    def chunk(self, chunk_id: str) -> Chunk | None:
        row = self.conn.execute("SELECT * FROM chunks WHERE chunk_id = ?", (chunk_id,)).fetchone()
        return self._row(row) if row else None

    def chunks(self) -> list[Chunk]:
        return [self._row(r) for r in self.conn.execute("SELECT * FROM chunks ORDER BY doc_id, version, position")]

    def documents(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM documents ORDER BY doc_id, version")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur]

    def _row(self, r) -> Chunk:
        (cid, doc_id, version, title, chunker, position, start, end, text, sections, pages, ef, et, access,
         language, doc_type, source) = r
        return Chunk(cid, doc_id, version, title, chunker, position, start, end, text, tuple(json.loads(sections)),
                     tuple(json.loads(pages)), ef, et or "", access, language, doc_type, source)

    def vectors(self) -> tuple[list[str], np.ndarray]:
        """All chunk IDs and their vectors (one row each), cached until the index changes."""
        if self._matrix is None:
            rows = self.conn.execute("SELECT chunk_id, vector FROM vectors ORDER BY chunk_id").fetchall()
            ids = [r[0] for r in rows]
            matrix = np.array([np.frombuffer(r[1], dtype=np.float32) for r in rows]) if rows else np.zeros((0, 0))
            self._matrix = (ids, matrix)
        return self._matrix

    def add_document(self, path: Path, source: str, chunker: str, embedder=None) -> int:
        doc = parse(path)
        m = doc.meta
        for name in ("doc_id", "version"):
            if not m.get(name):
                raise ValueError(f"{source}: the metadata has no {name}.")
        chunks = make_chunks(doc, source, chunker)
        self.conn.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                          (m["doc_id"], m["version"], m.get("title", ""), source, doc.format, file_hash(path),
                           m.get("effective_from", ""), m.get("effective_to", ""), m.get("owner", ""),
                           m.get("access", ""), m.get("language", ""), m.get("doc_type", "")))
        self.conn.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (c.chunk_id, c.doc_id, c.version, c.title, c.chunker, c.position, c.start, c.end, c.text,
             json.dumps(list(c.sections), ensure_ascii=False), json.dumps(list(c.pages)), c.effective_from,
             c.effective_to, c.access, c.language, c.doc_type, c.source) for c in chunks])
        self.keywords.add((c.chunk_id, c.text) for c in chunks)
        if embedder is not None and chunks:
            vectors = embedder.embed_passages([c.text for c in chunks])
            self.conn.executemany("INSERT INTO vectors VALUES (?, ?)",
                                  [(c.chunk_id, v.astype(np.float32).tobytes()) for c, v in zip(chunks, vectors)])
        self._matrix = None
        return len(chunks)

    def sync(self, folder: Path, chunker: str = "structure", embedder=None) -> SyncReport:
        """Rebuild the whole index from the documents in `folder`."""
        report = SyncReport()
        root = Path(folder).parent
        with self.conn:
            for table in ("documents", "chunks", "keyword_index", "vectors", "meta"):
                self.conn.execute(f"DELETE FROM {table}")
            for path in sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in SUFFIXES):
                report.chunks_added += self.add_document(path, path.relative_to(root).as_posix(), chunker, embedder)
                report.added.append(path.relative_to(root).as_posix())
            settings = {"chunker": chunker, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if embedder is not None:
                settings |= {"embedding_model": embedder.name, "embedding_revision": embedder.revision}
            self.set_meta(**settings)
        return report

    def close(self) -> None:
        self.conn.close()
