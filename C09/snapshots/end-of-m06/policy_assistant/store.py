"""The index: one SQLite file with the documents, their chunks, the keyword index and the vectors.

Tables:
  documents  one row per document version: metadata, the file and the SHA-256 of its bytes
  chunks     one row per chunk: its text, positions, sections, pages and the document's metadata
  keyword_index (FTS5) the chunks' text for BM25 (lexical.py)
  vectors    one row per chunk: its embedding (float32 bytes)
  meta       how the index was built: chunker, embedding model and revision, time of the last sync

`sync()` brings the index up to date with the folder of documents, and does only the work needed:
- a file whose content hash is unchanged is skipped (no parsing, no embedding);
- a new or changed file is parsed and chunked again; its old chunks, keyword rows and vectors are
  deleted first, so no old text stays searchable;
- a document whose file is gone is deleted from every table, including the keyword index and the
  vectors: a deletion must reach the index, not only the folder. Deletions run first, so a renamed
  file is removed under its old name and added under its new one;
- two files with the same document ID and version are refused (DuplicateDocument), and the index
  stays as it was: one document version must come from exactly one file.
A different chunker or embedding model cannot be mixed into an existing index: sync refuses, and
`--rebuild` starts a new one.
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
    """The index was built with another chunker or embedding model."""


class DuplicateDocument(ValueError):
    """Two files hold the same document ID and version."""


@dataclass
class SyncReport:
    added: list = field(default_factory=list)
    updated: list = field(default_factory=list)
    unchanged: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    chunks_added: int = 0
    chunks_removed: int = 0

    def line(self) -> str:
        return (f"{len(self.added)} added, {len(self.updated)} updated, {len(self.unchanged)} unchanged, "
                f"{len(self.removed)} removed | chunks: +{self.chunks_added} -{self.chunks_removed}")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)  # read from 2 threads when recording
        self.conn.executescript(SCHEMA)
        self.keywords = KeywordIndex(self.conn)
        self._matrix, self._matrix_generation, self._writes = None, None, 0

    # ------------------------------------------------------------ meta
    def meta(self) -> dict:
        return dict(self.conn.execute("SELECT key, value FROM meta"))

    def set_meta(self, **values) -> None:
        self.conn.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)", [(k, str(v)) for k, v in values.items()])

    # ------------------------------------------------------------ reading
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

    def generation(self) -> tuple[int, int]:
        """Changes when the index changes: through this Store (a write counter) or through another
        connection, for example `ingest` in another process (SQLite's data_version)."""
        return self.conn.execute("PRAGMA data_version").fetchone()[0], self._writes

    def vectors(self) -> tuple[list[str], np.ndarray]:
        """All chunk IDs and their vectors (one row each), kept in memory until the index changes."""
        if self._matrix is None or self._matrix_generation != self.generation():
            self._matrix_generation = self.generation()
            rows = self.conn.execute("SELECT chunk_id, vector FROM vectors ORDER BY chunk_id").fetchall()
            ids = [r[0] for r in rows]
            matrix = np.array([np.frombuffer(r[1], dtype=np.float32) for r in rows]) if rows else np.zeros((0, 0))
            self._matrix = (ids, matrix)
        return self._matrix

    # ------------------------------------------------------------ writing
    def check_settings(self, chunker: str, embedder) -> None:
        meta = self.meta()
        if meta.get("chunker") and meta["chunker"] != chunker:
            raise IndexMismatch(f"This index was built with the {meta['chunker']} chunker, not {chunker}. "
                                "Use --rebuild to start a new index.")
        if embedder is not None and meta.get("embedding_model") and (
                meta["embedding_model"], meta.get("embedding_revision")) != (embedder.name, embedder.revision):
            raise IndexMismatch(f"This index was built with {meta['embedding_model']} ({meta.get('embedding_revision')}), "
                                f"not {embedder.name} ({embedder.revision}). Vectors of two models cannot be mixed: "
                                "use --rebuild.")

    def remove_document(self, doc_id: str, version: str) -> int:
        """Delete a document version and everything made from it. Returns the number of chunks removed."""
        ids = [r[0] for r in self.conn.execute("SELECT chunk_id FROM chunks WHERE doc_id = ? AND version = ?",
                                               (doc_id, version))]
        self.keywords.remove(ids)
        self.conn.executemany("DELETE FROM vectors WHERE chunk_id = ?", [(i,) for i in ids])
        self.conn.execute("DELETE FROM chunks WHERE doc_id = ? AND version = ?", (doc_id, version))
        self.conn.execute("DELETE FROM documents WHERE doc_id = ? AND version = ?", (doc_id, version))
        self._writes += 1
        return len(ids)

    def add_document(self, path: Path, source: str, chunker: str, embedder=None) -> int:
        doc = parse(path)
        m = doc.meta
        for name in ("doc_id", "version"):
            if not m.get(name):
                raise ValueError(f"{source}: the metadata has no {name}.")
        other = self.conn.execute("SELECT file FROM documents WHERE doc_id = ? AND version = ?",
                                  (m["doc_id"], m["version"])).fetchone()
        if other:
            raise DuplicateDocument(f"{source} and {other[0]} are both {m['doc_id']} version {m['version']}. "
                                    "Keep one file per document version; a new version needs a new version number.")
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
        self._writes += 1
        return len(chunks)

    def sync(self, folder: Path, chunker: str = "structure", embedder=None) -> SyncReport:
        """Make the index match the documents in `folder` (see the module's description)."""
        self.check_settings(chunker, embedder)
        report = SyncReport()
        known = {r["file"]: r for r in self.documents()}
        root = Path(folder).parent
        files = {p.relative_to(root).as_posix(): p for p in sorted(Path(folder).iterdir())
                 if p.suffix.lower() in SUFFIXES}
        with self.conn:   # one transaction: if anything fails, the index stays as it was
            for source, old in known.items():           # 1. files that are gone
                if source not in files:
                    report.chunks_removed += self.remove_document(old["doc_id"], old["version"])
                    report.removed.append(source)
            for source, path in files.items():          # 2. new, changed and unchanged files
                old = known.get(source)
                if old and old["content_hash"] == file_hash(path):
                    report.unchanged.append(source)
                    continue
                if old:
                    report.chunks_removed += self.remove_document(old["doc_id"], old["version"])
                report.chunks_added += self.add_document(path, source, chunker, embedder)
                (report.updated if old else report.added).append(source)
            settings = {"chunker": chunker, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if embedder is not None:
                settings |= {"embedding_model": embedder.name, "embedding_revision": embedder.revision}
            self.set_meta(**settings)
        return report

    def close(self) -> None:
        self.conn.close()
