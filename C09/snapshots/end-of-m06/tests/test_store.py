"""The index: built from the folder; changes and deletions reach every table (keywords, vectors)."""

import shutil

import pytest

from policy_assistant.documents import CORPUS
from policy_assistant.store import IndexMismatch, Store


class FakeEmbedder:
    """A tiny stand-in for an embedding model (deterministic, no download): 4 numbers per text."""
    name, revision = "fake", "1"

    def embed_passages(self, texts):
        import numpy as np
        return np.array([[len(t), t.count("a"), t.count("e"), 1.0] for t in texts], dtype=np.float32)


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "corpus" / "documents"
    shutil.copytree(CORPUS / "documents", target)
    return target


def test_ingest_everything(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    report = store.sync(folder, "structure")
    assert len(report.added) == 36 and report.chunks_added == 185
    assert len(store.documents()) == 36 and len(store.chunks()) == 185
    hits = store.keywords.search("PK-2200-07", k=2)
    assert {store.chunk(h.id).doc_id for h in hits} == {"product-care-pw2200", "warranty-claims-procedure"}


def test_second_sync_does_nothing(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure")
    report = store.sync(folder, "structure")
    assert report.line() == "0 added, 0 updated, 36 unchanged, 0 removed | chunks: +0 -0"


def test_changed_document_is_replaced_everywhere(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure", FakeEmbedder())
    path = folder / "gift-cards.md"
    path.write_text(path.read_text().replace("from 25 to 500 dollars", "from 20 to 750 dollars"))
    report = store.sync(folder, "structure", FakeEmbedder())
    assert report.updated == ["documents/gift-cards.md"] and len(report.unchanged) == 35
    assert any(store.chunk(h.id).doc_id == "gift-cards" for h in store.keywords.search("750", k=5))
    assert not any(store.chunk(h.id).doc_id == "gift-cards" for h in store.keywords.search("500", k=50))
    ids, matrix = store.vectors()
    assert len(ids) == len(store.chunks())   # no vector left behind for the old chunks


def test_deleted_document_is_no_longer_searchable(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure", FakeEmbedder())
    assert store.keywords.search("staff discount 20%", k=1)
    (folder / "staff-discount-and-perks.md").unlink()
    report = store.sync(folder, "structure", FakeEmbedder())
    assert report.removed == ["documents/staff-discount-and-perks.md"]
    assert all(store.chunk(h.id).doc_id != "staff-discount-and-perks" for h in store.keywords.search("staff discount", k=50))
    rows = store.conn.execute("SELECT COUNT(*) FROM keyword_index WHERE item_id NOT IN (SELECT chunk_id FROM chunks)")
    assert rows.fetchone()[0] == 0
    ids, _ = store.vectors()
    assert set(ids) == {c.chunk_id for c in store.chunks()}


def test_models_and_chunkers_are_not_mixed(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure", FakeEmbedder())
    with pytest.raises(IndexMismatch):
        store.sync(folder, "fixed", FakeEmbedder())
    other = FakeEmbedder()
    other.name = "another-model"
    with pytest.raises(IndexMismatch):
        store.sync(folder, "structure", other)
