"""The policy collection: the inventory and the Markdown documents.

corpus/inventory.csv lists every document with its metadata (Grace's inventory). Most documents are
Markdown files with a front matter block between two '---' lines; four arrive as HTML or PDF and are
read by parse.py (Module 2).
"""

import csv
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
CORPUS = PROJECT / "corpus"
INVENTORY = CORPUS / "inventory.csv"


@dataclass(frozen=True)
class DocInfo:
    file: str             # path inside corpus/, for example documents/returns-policy.v3.md
    doc_id: str
    title: str
    version: str
    effective_from: str   # YYYY-MM-DD
    effective_to: str     # YYYY-MM-DD, or "" when the document has no end date
    owner: str
    access: str           # public or staff
    language: str         # en or fr
    doc_type: str         # policy, procedure, guide, help, notice, supplier
    format: str           # md, html or pdf

    @property
    def path(self) -> Path:
        return CORPUS / self.file


def load_inventory(path: Path = INVENTORY) -> list[DocInfo]:
    with path.open(encoding="utf-8", newline="") as f:
        return [DocInfo(**row) for row in csv.DictReader(f)]


def read_markdown(path: Path) -> tuple[dict, str]:
    """A Markdown file -> (front matter as a dict, body text)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, head, body = text.split("---\n", 2)
    meta = {}
    for line in head.strip().splitlines():
        name, value = line.split(":", 1)
        meta[name.strip()] = value.strip().strip('"')
    return meta, body.strip() + "\n"
