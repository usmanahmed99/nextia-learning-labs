"""The help-desk systems: the database, the documents, the write services and the audit log.

Nothing here reaches a real system. The database is a local SQLite file (work/helpdesk.sqlite, a
copy of data/helpdesk.sqlite) and the file area is a copy of data/vfs (work/vfs). The write services
(refund, return label, e-mail) record into the database. The audit log (a table in the database)
records who did what, to which tenant, with what result. It can be redacted (no secrets, no message
bodies) or raw (the weak version, which logs the message body). Every run of the assistant is also
stored in the `conversations` table.
"""

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from .config import redact
from .data import HOLIDAYS, SEED_DB, TODAY, VFS, WORK

PRACTICE_DB = WORK / "helpdesk.sqlite"


def business_days_between(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d += __import__("datetime").timedelta(days=1)
        if d.weekday() < 5 and d not in HOLIDAYS:
            n += 1
    return n


EXTRA_TABLES = """
CREATE TABLE IF NOT EXISTS audit_log (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, run_id TEXT,
                                      actor TEXT, tenant TEXT, action TEXT NOT NULL, result TEXT NOT NULL,
                                      detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS conversations (run_id TEXT PRIMARY KEY, tenant TEXT, case_id TEXT, ticket_id TEXT,
                                          customer_id TEXT, customer_name TEXT, customer_email TEXT, request TEXT,
                                          ticket_text TEXT, answer TEXT, outcome TEXT NOT NULL, created_at TEXT NOT NULL,
                                          expires_on TEXT);
"""


def reset_practice_db(path: Path | None = None) -> Path:
    """A fresh copy of the seed database and of the file area (the folder vfs/ next to the database)."""
    path = path or PRACTICE_DB
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SEED_DB, path)
    files = path.parent / "vfs"
    if files.exists():
        shutil.rmtree(files)
    shutil.copytree(VFS, files)
    with closing(sqlite3.connect(path)) as con:
        con.executescript(EXTRA_TABLES)
    return path


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class World:
    """One session's view of the systems. `redact_log` off is the weak version (logs message bodies)."""

    def __init__(self, db: Path | None = None, redact_log: bool = True):
        self.db = db or PRACTICE_DB
        if not self.db.exists() or not (self.db.parent / "vfs").exists():
            reset_practice_db(self.db)
        self.vfs = self.db.parent / "vfs"   # this world's copy of the file area
        with closing(sqlite3.connect(self.db)) as con:
            con.executescript(EXTRA_TABLES)   # the tables the app adds to the seed database
        self.redact_log = redact_log
        self.audit: list[dict] = []        # the events this World wrote (they are also in the audit_log table)
        self.run_id = ""                   # set by the assistant: every event of a run carries its run ID
        self._seq = 0

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        return con

    # ----- identity support (the membership table the server trusts)
    def role_in(self, sub: str, tenant: str) -> str | None:
        with closing(self._con()) as con:
            row = con.execute("SELECT role FROM memberships WHERE sub=? AND tenant=?", (sub, tenant)).fetchone()
            return row["role"] if row else None

    def is_platform_admin(self, sub: str) -> bool:
        with closing(self._con()) as con:
            row = con.execute("SELECT platform_admin FROM users WHERE sub=?", (sub,)).fetchone()
            return bool(row and row["platform_admin"])

    # ----- the audit log
    def log(self, actor: str, tenant: str, action: str, result: str, **detail) -> None:
        self._seq += 1
        if self.redact_log:
            detail = {k: (redact(v) if isinstance(v, str) else v) for k, v in detail.items()
                      if k not in ("message", "request", "body")}
        entry = {"seq": self._seq, "at": now(), "run": self.run_id, "actor": actor, "tenant": tenant,
                 "action": action, "result": result, **detail}
        self.audit.append(entry)
        with closing(self._con()) as con:
            con.execute("INSERT INTO audit_log (at,run_id,actor,tenant,action,result,detail) VALUES (?,?,?,?,?,?,?)",
                        (entry["at"], self.run_id, actor, tenant, action, result,
                         json.dumps(detail, ensure_ascii=False, sort_keys=True)))
            con.commit()

    def audit_rows(self) -> list[dict]:
        """Every event in the audit log table (all runs on this database), oldest first."""
        with closing(self._con()) as con:
            return [{**dict(r), "detail": json.loads(r["detail"])}
                    for r in con.execute("SELECT * FROM audit_log ORDER BY seq")]

    # ----- stored conversations (what the assistant keeps after a run)
    def save_conversation(self, row: dict) -> None:
        cols = ("run_id", "tenant", "case_id", "ticket_id", "customer_id", "customer_name", "customer_email",
                "request", "ticket_text", "answer", "outcome", "created_at", "expires_on")
        with closing(self._con()) as con:
            con.execute(f"INSERT OR REPLACE INTO conversations ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [row.get(c) for c in cols])
            con.commit()

    def conversations(self, customer_id: str | None = None) -> list[dict]:
        with closing(self._con()) as con:
            q, args = "SELECT * FROM conversations", []
            if customer_id:
                q, args = q + " WHERE customer_id=?", [customer_id]
            return [dict(r) for r in con.execute(q + " ORDER BY created_at", args)]

    # ----- reads
    def customer(self, customer_id: str, tenant: str | None = None):
        with closing(self._con()) as con:
            q = "SELECT * FROM customers WHERE customer_id=?"
            args = [customer_id]
            if tenant is not None:
                q += " AND tenant=?"
                args.append(tenant)
            row = con.execute(q, args).fetchone()
            return dict(row) if row else None

    def ticket(self, ticket_id: str, tenant: str | None = None):
        with closing(self._con()) as con:
            q = "SELECT * FROM tickets WHERE ticket_id=?"
            args = [ticket_id]
            if tenant is not None:
                q += " AND tenant=?"
                args.append(tenant)
            row = con.execute(q, args).fetchone()
            if not row:
                return None
            t = dict(row)
            t["attachments"] = json.loads(t["attachments"])
            return t

    def order(self, order_id: str, tenant: str | None = None):
        with closing(self._con()) as con:
            q = "SELECT * FROM orders WHERE order_id=?"
            args = [order_id]
            if tenant is not None:
                q += " AND tenant=?"
                args.append(tenant)
            row = con.execute(q, args).fetchone()
            if not row:
                return None
            o = dict(row)
            o["items"] = [dict(r) for r in con.execute(
                "SELECT line,item,quantity,unit_price FROM order_items WHERE order_id=? ORDER BY line", (order_id,))]
            o["refunds"] = [dict(r) for r in con.execute(
                "SELECT refund_id,amount,reason,created_at FROM refunds WHERE order_id=? ORDER BY created_at",
                (order_id,))]
            if o.get("delivered_on"):
                o["days_since_delivery"] = (TODAY - date.fromisoformat(o["delivered_on"])).days
            if o.get("shipped_on"):
                o["business_days_late"] = max(0, business_days_between(
                    date.fromisoformat(o["expected_by"]), TODAY)) if o.get("expected_by") else None
            return o

    def order_tenant(self, order_id: str) -> str | None:
        with closing(self._con()) as con:
            row = con.execute("SELECT tenant FROM orders WHERE order_id=?", (order_id,)).fetchone()
            return row["tenant"] if row else None

    def search_docs(self, query: str, tenant: str | None, access: tuple[str, ...] = ("public",), limit: int = 3):
        """Keyword search (SQLite FTS5, BM25 ranking): the best `limit` passages for ANY of the query's words.

        Each word of three letters or more becomes a quoted term, joined with OR, so a passage need not
        contain every word of the model's query (a plain MATCH of "return window policy" would need all three).
        """
        words = [w for w in "".join(c if c.isalnum() else " " for c in query.lower()).split() if len(w) > 2]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
        with closing(self._con()) as con:
            placeholders = ",".join("?" * len(access))
            sql = (f"SELECT d.passage_id,d.doc_id,d.title,d.section,d.text,d.version,d.tenant,d.access "
                   f"FROM documents_fts f JOIN documents d ON d.passage_id=f.passage_id "
                   f"WHERE documents_fts MATCH ? AND d.access IN ({placeholders})")
            args: list = [match, *access]
            if tenant is not None:
                sql += " AND d.tenant=?"
                args.append(tenant)
            sql += " ORDER BY bm25(documents_fts), d.passage_id LIMIT ?"
            args.append(limit)
            return [dict(r) for r in con.execute(sql, args)]

    def file_metadata(self, path: str):
        with closing(self._con()) as con:
            row = con.execute("SELECT * FROM files WHERE path=?", (path,)).fetchone()
            return dict(row) if row else None

    # ----- writes (recorded into the database)
    def write(self, tool: str, tenant: str, args: dict, actor: str, approval_id: str | None) -> dict:
        with closing(self._con()) as con:
            # The next number for this kind of write: IS-0001, CR-0001, SE-0001 ... (the same on every run).
            table, column = {"issue_refund": ("refunds", "refund_id"), "create_return_label": ("return_labels", "label_id"),
                             "send_email": ("emails", "email_id")}.get(tool, ("", ""))
            if not table:
                raise ValueError(f"not a write tool: {tool}")
            prefix = tool[:2].upper()
            count = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE ?", (prefix + "-%",)).fetchone()[0]
            ident = f"{prefix}-{count + 1:04d}"
            if tool == "issue_refund":
                con.execute("INSERT INTO refunds VALUES (?,?,?,?,?,?,?,?)",
                            (ident, tenant, args["order_id"], args["amount"], args.get("reason", ""), actor,
                             approval_id, now()))
            elif tool == "create_return_label":
                con.execute("INSERT INTO return_labels VALUES (?,?,?,?,?,?)",
                            (ident, tenant, args["order_id"], actor, approval_id, now()))
            elif tool == "send_email":
                con.execute("INSERT INTO emails VALUES (?,?,?,?,?,?,?,?)",
                            (ident, tenant, args["to"], args.get("subject", ""), args.get("body", ""), actor,
                             approval_id, now()))
            else:
                raise ValueError(f"not a write tool: {tool}")
            con.commit()
            return {"id": ident, "tool": tool, "order_id": args.get("order_id"), "to": args.get("to")}

    def changes(self, tenant: str | None = None) -> dict:
        with closing(self._con()) as con:
            out = {}
            for table in ("refunds", "return_labels", "emails"):
                q = f"SELECT * FROM {table}"
                args: list = []
                if tenant is not None:
                    q += " WHERE tenant=?"
                    args.append(tenant)
                out[table] = [dict(r) for r in con.execute(q + " ORDER BY created_at", args)]
            return out
