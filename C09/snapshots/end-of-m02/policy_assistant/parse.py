"""Parse Markdown, HTML and PDF documents into the same clean form, keeping where each part came from.

Every document becomes a ParsedDocument: its metadata and a list of blocks (the title, section
headings, paragraphs and lists, tables). Each block knows its section and, for a PDF, its page.
`ParsedDocument.text` joins the blocks with blank lines; each block's `start`/`end` are its character
positions in that text, so that a chunk can always be traced back to its blocks, sections and pages.

What each format needs:
- Markdown: read the front matter; remove ** bold marks.
- HTML: keep only the <article> (drop navigation, cookie banner, breadcrumbs, related articles,
  footer, scripts); metadata from <meta> tags; table cells joined with " | ".
- PDF (pypdf): drop the lines repeated on every page and the lines in the top and bottom margins
  (header, footer, "Page 1 of 2"); read the bullet, which pypdf returns as the control character
  U+007F; find headings by
  font size; rebuild table rows from the position of each line; join words hyphenated at line ends;
  metadata from the PDF's Keywords field.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from .documents import read_markdown


@dataclass
class Block:
    kind: str                 # title, heading, text or table
    text: str
    section: str = ""         # the heading of the section that holds the block ("" for the title)
    page: int | None = None   # 1-based page number for a PDF; None for Markdown and HTML
    start: int = 0
    end: int = 0


@dataclass
class ParsedDocument:
    path: str
    format: str
    meta: dict
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


def clean(text: str) -> str:
    """Normalise Unicode (NFC), turn non-breaking spaces into spaces and collapse runs of spaces."""
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


def finish(doc: ParsedDocument) -> ParsedDocument:
    """Set the section of every block and its character positions in doc.text."""
    section, pos = "", 0
    for b in doc.blocks:
        if b.kind == "heading":
            section = b.text
        b.section = "" if b.kind == "title" else section
        b.start, b.end = pos, pos + len(b.text)
        pos = b.end + 2
    return doc


# ---------------------------------------------------------------- Markdown

def parse_markdown(path: Path) -> ParsedDocument:
    meta, body = read_markdown(path)
    doc = ParsedDocument(str(path), "md", meta)
    para: list[str] = []
    kind = "text"

    def flush():
        nonlocal para, kind
        if para:
            doc.blocks.append(Block(kind, clean_lines(para)))
        para, kind = [], "text"

    for line in body.splitlines():
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", line.strip())
        if not s:
            flush()
        elif s.startswith("# "):
            flush(); doc.blocks.append(Block("title", clean(s[2:])))
        elif s.startswith("## "):
            flush(); doc.blocks.append(Block("heading", clean(s[3:])))
        elif s.startswith("|"):
            if kind != "table":
                flush(); kind = "table"
            cells = [clean(c) for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                para.append(" | ".join(cells))
        else:
            if kind == "table":
                flush()
            para.append(s)
    flush()
    return finish(doc)


def clean_lines(lines: list[str]) -> str:
    """Join paragraph lines with spaces, but keep list items and table rows on their own lines."""
    out: list[str] = []
    for line in lines:
        if out and not line.startswith("- ") and " | " not in line and not out[-1].startswith("- "):
            out[-1] += " " + line
        else:
            out.append(line)
    return "\n".join(clean(x) for x in out)


# ---------------------------------------------------------------- HTML

class _ArticleParser(HTMLParser):
    SKIP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict = {}
        self.blocks: list[Block] = []
        self.in_article = 0
        self.skip = 0
        self.tag: str | None = None
        self.buf: list[str] = []
        self.row: list[str] = []
        self.rows: list[str] = []
        self.items: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and "name" in a:
            self.meta[a["name"]] = a.get("content", "")
        if tag == "article":
            self.in_article += 1
        if not self.in_article:
            return
        if tag in self.SKIP or "doc-meta" in (a.get("class") or ""):
            self.skip += 1
        elif tag in ("h1", "h2", "p", "li", "td", "th"):
            self.tag, self.buf = tag, []
        elif tag == "table":
            self.rows = []
        elif tag == "tr":
            self.row = []
        elif tag == "ul":
            self.items = []

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_article -= 1
            return
        if not self.in_article:
            return
        if self.skip:
            if tag in self.SKIP or tag == "p":
                self.skip -= 1
            return
        text = clean("".join(self.buf))
        if tag == "h1":
            self.blocks.append(Block("title", text))
        elif tag == "h2":
            self.blocks.append(Block("heading", text))
        elif tag == "p" and text:
            self.blocks.append(Block("text", text))
        elif tag == "li":
            self.items.append("- " + text)
        elif tag == "ul":
            self.blocks.append(Block("text", "\n".join(self.items)))
        elif tag in ("td", "th"):
            self.row.append(text)
        elif tag == "tr":
            self.rows.append(" | ".join(self.row).rstrip())
        elif tag == "table":
            self.blocks.append(Block("table", "\n".join(self.rows)))
        if tag in ("h1", "h2", "p", "li", "td", "th"):
            self.tag, self.buf = None, []

    def handle_data(self, data):
        if self.in_article and not self.skip and self.tag:
            self.buf.append(data)


def parse_html(path: Path) -> ParsedDocument:
    p = _ArticleParser()
    p.feed(path.read_text(encoding="utf-8"))
    return finish(ParsedDocument(str(path), "html", p.meta, p.blocks))


# ---------------------------------------------------------------- PDF

PAGE_HEIGHT, MARGIN = 792, 60          # US Letter, in points
BULLETS = {"\u2022", "\u007f", "\u0095"}  # pypdf returns Helvetica's bullet as U+007F


@dataclass
class _Line:
    page: int
    x: float
    y: float
    font: str
    size: float
    text: str


def pdf_lines(path: Path) -> tuple[list[_Line], dict, int]:
    """Every line of text with its page, position, font and size (pypdf's visitor), and the metadata."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    lines: list[_Line] = []
    for n, page in enumerate(reader.pages, 1):
        def visit(text, cm, tm, font_dict, font_size, n=n):
            if text.strip():
                font = str((font_dict or {}).get("/BaseFont", ""))
                lines.append(_Line(n, round(tm[4], 1), round(tm[5], 1), font, float(font_size), text.strip("\n")))
        page.extract_text(visitor_text=visit)
    info = reader.metadata or {}
    meta = dict(part.split("=", 1) for part in str(info.get("/Keywords", "")).split("; ") if "=" in part)
    return lines, meta, len(reader.pages)


def dehyphenate(lines: list[str]) -> str:
    """Join lines into one paragraph; 'greenhou-' + 'ses' becomes 'greenhouses'."""
    out = ""
    for line in lines:
        line = line.strip()
        if out.endswith("-") and len(out) > 1 and out[-2].isalpha() and line[:1].islower():
            out = out[:-1] + line
        else:
            out = (out + " " + line).strip()
    return out


def parse_pdf(path: Path) -> ParsedDocument:
    lines, meta, npages = pdf_lines(path)
    # 1. Lines repeated on every page (same text, same place) are the header and the footer.
    seen: dict[tuple, set] = {}
    for ln in lines:
        key = (re.sub(r"\d+", "#", ln.text.strip()), ln.y)
        seen.setdefault(key, set()).add(ln.page)
    repeated = {k for k, pages in seen.items() if len(pages) == npages and npages > 1}
    # 2. A one-page PDF has nothing to compare: also drop the top and bottom margins (60 points of 792).
    body = [ln for ln in lines if (re.sub(r"\d+", "#", ln.text.strip()), ln.y) not in repeated
            and MARGIN < ln.y < PAGE_HEIGHT - MARGIN]

    doc = ParsedDocument(str(path), "pdf", meta)
    para: list[str] = []
    para_page = None
    table: list[_Line] = []
    body_size = 10.5

    def flush_para():
        nonlocal para, para_page
        if para:
            doc.blocks.append(Block("text", dehyphenate(para), page=para_page))
        para, para_page = [], None

    def flush_table():
        nonlocal table
        if table:
            doc.blocks.append(Block("table", rebuild_table(table), page=table[0].page))
        table = []

    prev = None
    for ln in body:
        text = clean(ln.text)
        if ln.size >= 15:
            flush_para(); flush_table()
            doc.blocks.append(Block("title", text, page=ln.page))
        elif ln.size >= 12 and "Bold" in ln.font:
            flush_para(); flush_table()
            doc.blocks.append(Block("heading", text, page=ln.page))
        elif ln.size < body_size - 0.5:          # the smaller font of table cells
            flush_para()
            table.append(ln)
        else:
            flush_table()
            # A new paragraph starts after a larger vertical gap, on a new page, or with a bullet.
            gap = prev is not None and prev.page == ln.page and prev.y - ln.y > 16
            new_page = prev is not None and prev.page != ln.page
            if ln.text.strip() in BULLETS:
                flush_para()
                para, para_page = ["-"], ln.page
                prev = ln
                continue
            if para and para != ["-"] and (gap or (new_page and para[0] != "-")) and ln.x <= 72.5:
                flush_para()
            if para == ["-"]:
                para = ["- " + text]
            else:
                if not para:
                    para_page = ln.page
                para.append(text)
        prev = ln
    flush_para(); flush_table()
    # Consecutive list items become one list block, as in the other formats.
    merged: list[Block] = []
    for b in doc.blocks:
        if merged and b.kind == "text" and b.text.startswith("- ") and merged[-1].kind == "text" \
                and merged[-1].text.startswith("- "):
            merged[-1].text += "\n" + b.text
        else:
            merged.append(b)
    doc.blocks = merged
    return finish(doc)


def rebuild_table(cells: list[_Line]) -> str:
    """Rebuild rows from line positions: a cell's lines are 12 points apart; a new row starts lower."""
    columns = sorted({c.x for c in cells})
    rows: list[list[_Line]] = []
    last_y, last_page = None, None
    for c in sorted(cells, key=lambda c: (c.page, -c.y, c.x)):
        if last_y is None or c.page != last_page or last_y - c.y > 15:
            rows.append([])
        rows[-1].append(c)
        last_y, last_page = c.y, c.page
    out = []
    for row in rows:
        texts = []
        for x in columns:
            parts = [c.text for c in sorted(row, key=lambda c: -c.y) if c.x == x]
            texts.append(dehyphenate(parts))
        out.append(" | ".join(t.strip() for t in texts).rstrip())
    return "\n".join(out)


# ---------------------------------------------------------------- any format

def parse(path: Path) -> ParsedDocument:
    suffix = Path(path).suffix.lower()
    if suffix == ".md":
        return parse_markdown(Path(path))
    if suffix in (".html", ".htm"):
        return parse_html(Path(path))
    if suffix == ".pdf":
        return parse_pdf(Path(path))
    raise ValueError(f"Cannot parse {path}: only .md, .html and .pdf are supported.")
