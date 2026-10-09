import sqlite3

from policy_assistant.lexical import KeywordIndex, fts_query, words


def make(items):
    index = KeywordIndex(sqlite3.connect(":memory:"))
    index.add(items)
    return index


def test_query_quotes_every_word_and_splits_codes():
    assert words("Which pump kit fits the PW-2200?") == ["which", "pump", "kit", "fits", "the", "pw", "2200"]
    assert fts_query("NOT a code") == '"not" OR "a" OR "code"'   # NOT is a word here, not an operator


def test_bm25_prefers_the_rare_word():
    index = make([("a", "the kettle and the toaster"), ("b", "the kettle"), ("c", "the toaster and the lamp")])
    hits = index.search("kettle lamp", k=3)
    # "lamp" occurs once in the collection, "kettle" twice: the item with the rare word wins.
    assert hits[0].id == "c"
    assert [h.rank for h in hits] == [1, 2, 3]
    assert hits[0].score > hits[1].score


def test_exact_code_and_accents():
    index = make([("pw", "Pump kit | PK-2200-07 | fits the PW-2200 only"), ("fr", "Larkfield ne vend pas de garantie prolongée.")])
    assert index.search("PK-2200-07", k=1)[0].id == "pw"
    assert index.search("garantie prolongee", k=1)[0].id == "fr"   # accents removed by the tokenizer


def test_allowed_is_applied_before_the_top_k():
    index = make([("staff", "goodwill credit 25 dollars"), ("public", "store credit never expires")])
    hits = index.search("credit", k=1, allowed=lambda i: i == "public")
    assert [h.id for h in hits] == ["public"]


def test_remove():
    index = make([("x", "deleted text"), ("y", "kept text")])
    index.remove(["x"])
    assert [h.id for h in index.search("text", k=5)] == ["y"]
