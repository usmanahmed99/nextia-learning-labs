"""The index: built from the folder of documents (rebuilt from scratch every time, for now)."""

from policy_assistant.documents import CORPUS
from policy_assistant.store import Store


def test_ingest_everything(tmp_path):
    store = Store(tmp_path / "index.sqlite")
    report = store.sync(CORPUS / "documents", "structure")
    assert len(report.added) == 36 and report.chunks_added == 185
    assert len(store.documents()) == 36 and len(store.chunks()) == 185
    hits = store.keywords.search("PK-2200-07", k=2)
    assert {store.chunk(h.id).doc_id for h in hits} == {"product-care-pw2200", "warranty-claims-procedure"}


def test_a_second_ingest_gives_the_same_index(tmp_path):
    store = Store(tmp_path / "index.sqlite")
    store.sync(CORPUS / "documents", "structure")
    before = [c.chunk_id for c in store.chunks()]
    report = store.sync(CORPUS / "documents", "structure")
    assert report.line() == "36 documents, 185 chunks (rebuilt from scratch)"
    assert [c.chunk_id for c in store.chunks()] == before        # stable IDs: the same chunks, the same IDs


def test_every_chunk_is_traceable(tmp_path):
    store = Store(tmp_path / "index.sqlite")
    store.sync(CORPUS / "documents", "fixed")
    for c in store.chunks():
        assert c.source.startswith("documents/") and c.doc_id and c.version and c.end > c.start
    pdf = [c for c in store.chunks() if c.source.endswith(".pdf")]
    assert pdf and all(c.pages for c in pdf)
