"""The index: built from the folder; changes and deletions reach every table (keywords, vectors)."""

import shutil

import pytest

from policy_assistant.documents import CORPUS
from policy_assistant.store import DuplicateDocument, IndexMismatch, Store


class FakeEmbedder:
    """A tiny stand-in for an embedding model (deterministic, no download): 4 numbers per text."""
    name, revision = "fake", "1"

    def embed_passages(self, texts):
        import numpy as np
        return np.array([[len(t), t.count("a"), t.count("e"), 1.0] for t in texts], dtype=np.float32)

    embed_queries = embed_passages


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


def test_a_renamed_file_is_moved_not_doubled(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure")
    (folder / "gift-cards.md").rename(folder / "gift-cards-2025.md")
    report = store.sync(folder, "structure")
    assert report.removed == ["documents/gift-cards.md"] and report.added == ["documents/gift-cards-2025.md"]
    assert len(store.chunks()) == 185


def test_two_files_with_one_document_version_are_refused(tmp_path, folder):
    store = Store(tmp_path / "index.sqlite")
    store.sync(folder, "structure")
    shutil.copyfile(folder / "gift-cards.md", folder / "gift-cards-copy.md")
    with pytest.raises(DuplicateDocument):
        store.sync(folder, "structure")
    assert len(store.documents()) == 36 and len(store.chunks()) == 185   # nothing changed


def test_a_running_assistant_sees_the_deletion(tmp_path, folder):
    """A long-running process keeps chunks and vectors in memory. When ingest (another connection,
    another process) removes a document, the next search must not return it from memory."""
    from policy_assistant.search import Retriever

    Store(tmp_path / "index.sqlite").sync(folder, "structure", FakeEmbedder())
    running = Retriever(Store(tmp_path / "index.sqlite"), FakeEmbedder())
    before = {r.chunk.doc_id for r in running.search("staff discount", "dense", 185)}
    (folder / "staff-discount-and-perks.md").unlink()
    Store(tmp_path / "index.sqlite").sync(folder, "structure", FakeEmbedder())   # like ingest, elsewhere
    after = {r.chunk.doc_id for r in running.search("staff discount", "dense", 185)}
    assert "staff-discount-and-perks" in before and "staff-discount-and-perks" not in after


def test_audit_finds_recorded_answers_that_cite_removed_or_obsolete_passages(tmp_path, folder, capsys):
    """The recorded answers are an answer cache: after a deletion or a new version, some of them
    cite a passage that the index no longer serves for their question."""
    from policy_assistant.__main__ import main

    index = str(tmp_path / "index.sqlite")
    Store(index).sync(folder, "structure")
    main(["--index", index, "audit"])
    assert capsys.readouterr().out.strip().endswith("| 0 citations to passages that are removed, not in force or not allowed")
    (folder / "holiday-returns-2025.md").unlink()                  # removed
    v1 = folder / "gift-cards.md"                                    # version 1 ends before Q63's date
    v1.write_text(v1.read_text().replace("effective_from: 2025-06-01\n", "effective_from: 2025-06-01\neffective_to: 2026-10-08\n"))
    Store(index).sync(folder, "structure")
    main(["--index", index, "audit"])
    out = capsys.readouterr().out
    assert "Q25" in out and "removed from the index" in out
    assert "Q63" in out and "gift-cards v1 is not in force on 2026-10-09" in out
