"""Three ways to cut a parsed document into chunks.

- fixed:     windows of SIZE words, one after the other. Simple; it cuts through sentences, headings
             and tables.
- overlap:   windows of SIZE words that start every SIZE - OVERLAP words, so that a sentence cut at
             the end of one chunk is whole in the next. More chunks, repeated text.
- structure: one chunk per section (from its heading to the next heading). A section longer than
             MAX_WORDS is split between blocks, never inside a table. Each chunk starts with the
             document title (and the section heading when a part does not start with it), so that a
             chunk keeps its context: "Specifications" alone does not say which pressure washer.

Every chunk keeps its character positions in the parsed text, so it can be traced to its source.
"""

import re

from .metadata import Chunk, make_chunk
from .parse import ParsedDocument

SIZE = 100        # words per fixed or overlapping chunk
OVERLAP = 25      # words repeated between two overlapping chunks
MAX_WORDS = 200   # longest structure chunk, unless a single table is longer
CHUNKERS = ("fixed", "overlap", "structure")


def word_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in re.finditer(r"\S+", text)]


def windows(doc: ParsedDocument, source: str, name: str, size: int, step: int) -> list[Chunk]:
    words = word_spans(doc.text)
    chunks, i = [], 0
    while i < len(words):
        part = words[i:i + size]
        chunks.append(make_chunk(doc, source, name, len(chunks), part[0][0], part[-1][1]))
        if i + size >= len(words):
            break
        i += step
    return chunks


def fixed(doc: ParsedDocument, source: str, size: int = SIZE) -> list[Chunk]:
    return windows(doc, source, "fixed", size, size)


def overlapping(doc: ParsedDocument, source: str, size: int = SIZE, overlap: int = OVERLAP) -> list[Chunk]:
    return windows(doc, source, "overlap", size, size - overlap)


def structure(doc: ParsedDocument, source: str, max_words: int = MAX_WORDS) -> list[Chunk]:
    title = doc.meta.get("title", "")
    sections: list[list] = []
    for b in doc.blocks:
        if b.kind == "heading" or not sections:
            sections.append([])
        if b.kind != "title":
            sections[-1].append(b)
    chunks: list[Chunk] = []
    for blocks in sections:
        if not blocks:
            continue
        heading = blocks[0].text if blocks[0].kind == "heading" else ""
        part: list = []
        for b in blocks:
            words = sum(len(x.text.split()) for x in part)
            if part and words + len(b.text.split()) > max_words:
                chunks.append(_part(doc, source, part, title, heading, len(chunks)))
                part = []
            part.append(b)
        chunks.append(_part(doc, source, part, title, heading, len(chunks)))
    return chunks


def _part(doc: ParsedDocument, source: str, blocks: list, title: str, heading: str, position: int) -> Chunk:
    start, end = blocks[0].start, blocks[-1].end
    prefix = title if blocks[0].kind == "heading" or not heading else f"{title}\n{heading}"
    return make_chunk(doc, source, "structure", position, start, end, f"{prefix}\n{doc.text[start:end]}")


def chunk(doc: ParsedDocument, source: str, method: str = "structure") -> list[Chunk]:
    if method == "fixed":
        return fixed(doc, source)
    if method == "overlap":
        return overlapping(doc, source)
    if method == "structure":
        return structure(doc, source)
    raise ValueError(f"Unknown chunker {method!r}: use one of {', '.join(CHUNKERS)}.")
