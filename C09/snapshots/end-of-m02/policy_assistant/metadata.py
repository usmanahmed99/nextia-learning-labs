"""Chunks and their metadata: a stable ID, the document, version, dates, access, section and pages.

A chunk ID is the first 12 hexadecimal characters of SHA-256 over "doc_id|version|start|end", where
start and end are the chunk's character positions in the parsed document. So:
- the same chunk gets the same ID every time the collection is ingested (a citation stays valid);
- a new version of a document gives new IDs (an answer never cites version 4 with a version-3 ID);
- adding or removing another document changes no ID (a counter would shift every later chunk).
"""

import hashlib
from dataclasses import asdict, dataclass

from .parse import ParsedDocument


def chunk_id(doc_id: str, version: str, start: int, end: int) -> str:
    return hashlib.sha256(f"{doc_id}|{version}|{start}|{end}".encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    version: str
    title: str
    chunker: str
    position: int          # 0, 1, 2 ... in the document (for reading order only; not part of the ID)
    start: int             # character positions of the source text in ParsedDocument.text
    end: int
    text: str              # the text that is indexed and shown to the model
    sections: tuple        # the section headings that the chunk covers
    pages: tuple           # PDF pages (empty for Markdown and HTML)
    effective_from: str
    effective_to: str      # "" when the document has no end date
    access: str            # public or staff
    language: str
    doc_type: str
    source: str            # the file it came from, inside corpus/

    @property
    def section(self) -> str:
        return self.sections[0] if self.sections else ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sections"], d["pages"] = list(self.sections), list(self.pages)
        return d


def make_chunk(doc: ParsedDocument, source: str, chunker: str, position: int, start: int, end: int,
               text: str | None = None) -> Chunk:
    """A chunk over doc.text[start:end] with the metadata of the blocks it overlaps."""
    meta = doc.meta
    covered = [b for b in doc.blocks if b.start < end and b.end > start]
    sections = tuple(dict.fromkeys(b.section for b in covered if b.section))
    pages = tuple(sorted({b.page for b in covered if b.page is not None}))
    return Chunk(
        chunk_id=chunk_id(meta["doc_id"], meta["version"], start, end),
        doc_id=meta["doc_id"], version=meta["version"], title=meta.get("title", ""), chunker=chunker,
        position=position, start=start, end=end, text=text if text is not None else doc.text[start:end],
        sections=sections, pages=pages, effective_from=meta.get("effective_from", ""),
        effective_to=meta.get("effective_to", ""), access=meta.get("access", "staff"),
        language=meta.get("language", "en"), doc_type=meta.get("doc_type", ""), source=source,
    )
