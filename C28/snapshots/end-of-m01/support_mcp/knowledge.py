"""The support knowledge: policy documents and tickets of two organizations.

This is the business service that the MCP server exposes. It is plain Python: no protocol here.
Every function takes the organization (the tenant) as a required argument, so a lookup can
never cross from one organization to the other. The data is synthetic (data/dataset.md).

The data lives in an in-memory SQLite database, loaded from data/ when the process starts.
Search uses SQLite FTS5 with BM25 ranking: simple, and good enough here. This project is about
the protocol, not about retrieval quality.

Try it:  python -m support_mcp.knowledge search larkfield "return a damaged item"
"""

import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
TENANTS = ("larkfield", "bramble")
STAFF_ROLES = ("owner", "staff")  # who may read documents marked "staff"


@dataclass(frozen=True)
class Hit:
    doc_id: str
    title: str
    snippet: str
    score: float


class NotFound(Exception):
    """The record does not exist in this organization (the same answer when it exists elsewhere)."""


class Knowledge:
    def __init__(self, data_dir: Path = DATA):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE documents (tenant TEXT, doc_id TEXT, version INTEGER, title TEXT,
                doc_type TEXT, access TEXT, effective_from TEXT, body TEXT,
                PRIMARY KEY (tenant, doc_id));
            CREATE VIRTUAL TABLE documents_fts USING fts5(title, body, tenant UNINDEXED,
                doc_id UNINDEXED, access UNINDEXED);
            CREATE TABLE tickets (tenant TEXT, ticket_id TEXT, data TEXT, PRIMARY KEY (tenant, ticket_id));
            """
        )
        for line in (data_dir / "documents.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            self.db.execute(
                "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                (
                    d["tenant"],
                    d["doc_id"],
                    d["version"],
                    d["title"],
                    d["doc_type"],
                    d["access"],
                    d["effective_from"],
                    d["body"],
                ),
            )
            self.db.execute(
                "INSERT INTO documents_fts VALUES (?,?,?,?,?)",
                (d["title"], d["body"], d["tenant"], d["doc_id"], d["access"]),
            )
        for line in (data_dir / "tickets.jsonl").read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            self.db.execute("INSERT INTO tickets VALUES (?,?,?)", (t["tenant"], t["ticket_id"], line))

    @staticmethod
    def _check_tenant(tenant: str) -> None:
        if tenant not in TENANTS:
            raise NotFound("Not found.")

    def search(self, tenant: str, query: str, limit: int = 3, staff: bool = False) -> list[Hit]:
        """The best `limit` documents of one organization for the words of `query` (BM25)."""
        self._check_tenant(tenant)
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 3]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in words)  # any word; BM25 ranks the best first
        access = ("public", "staff") if staff else ("public",)
        rows = self.db.execute(
            f"""SELECT doc_id, title, snippet(documents_fts, 1, '', '', ' … ', 24) AS snip,
                       bm25(documents_fts) AS score
                FROM documents_fts
                WHERE documents_fts MATCH ? AND tenant = ? AND access IN ({",".join("?" * len(access))})
                ORDER BY score LIMIT ?""",
            (match, tenant, *access, limit),
        ).fetchall()
        return [Hit(r["doc_id"], r["title"], " ".join(r["snip"].split()), round(-r["score"], 3)) for r in rows]

    def documents(self, tenant: str, staff: bool = False) -> list[dict]:
        """The organization's documents (without their text), in a stable order."""
        self._check_tenant(tenant)
        access = ("public", "staff") if staff else ("public",)
        rows = self.db.execute(
            f"""SELECT doc_id, version, title, doc_type, access FROM documents
                WHERE tenant = ? AND access IN ({",".join("?" * len(access))}) ORDER BY doc_id""",
            (tenant, *access),
        ).fetchall()
        return [dict(r) for r in rows]

    def document(self, tenant: str, doc_id: str, staff: bool = False) -> dict:
        self._check_tenant(tenant)
        r = self.db.execute("SELECT * FROM documents WHERE tenant = ? AND doc_id = ?", (tenant, doc_id)).fetchone()
        if r is None or (r["access"] == "staff" and not staff):
            raise NotFound("Not found.")
        return dict(r)

    def ticket(self, tenant: str, ticket_id: str) -> dict:
        """One ticket of this organization. A ticket of the other organization is 'not found' too."""
        self._check_tenant(tenant)
        r = self.db.execute(
            "SELECT data FROM tickets WHERE tenant = ? AND ticket_id = ?", (tenant, ticket_id)
        ).fetchone()
        if r is None:
            raise NotFound("Not found.")
        return json.loads(r["data"])

    def counts(self) -> dict:
        out = {}
        for tenant in TENANTS:
            out[tenant] = {
                "documents": self.db.execute("SELECT count(*) FROM documents WHERE tenant=?", (tenant,)).fetchone()[0],
                "tickets": self.db.execute("SELECT count(*) FROM tickets WHERE tenant=?", (tenant,)).fetchone()[0],
            }
        return out


def main(argv: list[str]) -> int:
    k = Knowledge()
    if not argv or argv[0] == "counts":
        for tenant, c in k.counts().items():
            print(f"{tenant}: {c['documents']} documents, {c['tickets']} tickets")
        return 0
    if argv[0] == "search" and len(argv) >= 3:
        for h in k.search(argv[1], " ".join(argv[2:])):
            print(f"{h.score:6.2f}  {h.doc_id}: {h.title}\n        {h.snippet}")
        return 0
    if argv[0] == "ticket" and len(argv) == 3:
        try:
            t = k.ticket(argv[1], argv[2])
        except NotFound:
            print("Not found.")
            return 1
        print(f"{t['ticket_id']} ({t['status']}): {t['subject']}\n{t['body']}")
        return 0
    print("usage: python -m support_mcp.knowledge counts | search TENANT WORDS | ticket TENANT ID")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
