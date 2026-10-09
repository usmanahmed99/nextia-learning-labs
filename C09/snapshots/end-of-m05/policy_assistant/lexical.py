"""Keyword search with SQLite full-text search (FTS5) and BM25.

FTS5 keeps an inverted index: for every word, the items that contain it. BM25 scores an item higher
when it contains the query's words often (term frequency, with diminishing returns), when those words
are rare in the collection (inverse document frequency), and when the item is short.
SQLite's bm25() returns lower numbers for better matches; `search` turns them round, so that a
higher score is better, as with every other search method in this project.

The tokenizer `unicode61 remove_diacritics 2` lowercases words and removes accents (é -> e), so a
French question matches French text written with or without accents. It splits "PW-2200" into "pw" and
"2200": the query is split the same way, so exact product codes still match.
"""

import re
import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(frozen=True)
class Hit:
    id: str
    score: float
    rank: int  # 1 = best


def words(text: str) -> list[str]:
    """The query's words, lowercased, without duplicates, in order."""
    return list(dict.fromkeys(w.lower() for w in re.findall(r"\w+", text)))


def fts_query(text: str) -> str:
    """'Which pump kit fits the PW-2200?' -> '"which" OR "pump" OR ... OR "pw" OR "2200"'.

    Every word is quoted, so FTS5 never reads a word as an operator (AND, OR, NOT, NEAR, -).
    OR means that an item needs only some of the words; BM25 ranks the items with more of them,
    and with rarer ones, higher.
    """
    return " OR ".join(f'"{w}"' for w in words(text))


class KeywordIndex:
    """An FTS5 table of (item ID, text) inside a SQLite database."""

    TABLE = "keyword_index"

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {self.TABLE} USING fts5("
                     "item_id UNINDEXED, text, tokenize = 'unicode61 remove_diacritics 2')")

    def add(self, items: Iterable[tuple[str, str]]) -> None:
        self.conn.executemany(f"INSERT INTO {self.TABLE} (item_id, text) VALUES (?, ?)", list(items))

    def remove(self, ids: Iterable[str]) -> None:
        self.conn.executemany(f"DELETE FROM {self.TABLE} WHERE item_id = ?", [(i,) for i in ids])

    def search(self, query: str, k: int = 5, allowed: Callable[[str], bool] | None = None) -> list[Hit]:
        """The k best items for the query. `allowed(item_id)` removes items before the top k is taken."""
        q = fts_query(query)
        if not q:
            return []
        rows = self.conn.execute(
            f"SELECT item_id, bm25({self.TABLE}) FROM {self.TABLE} WHERE {self.TABLE} MATCH ? "
            f"ORDER BY bm25({self.TABLE}), item_id", (q,)).fetchall()
        hits = [(item_id, -score) for item_id, score in rows if allowed is None or allowed(item_id)]
        return [Hit(item_id, round(score, 4), rank) for rank, (item_id, score) in enumerate(hits[:k], 1)]
