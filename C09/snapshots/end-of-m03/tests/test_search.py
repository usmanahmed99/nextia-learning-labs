"""Search on the real collection with the real local models (downloaded once: about 1 GB in all)."""

import pytest

from policy_assistant.documents import CORPUS
from policy_assistant.embed import LocalEmbedder, RecordedEmbedder, RecordingNotFound
from policy_assistant.evaluate import load_questions
from policy_assistant.filters import Filters
from policy_assistant.search import Retriever
from policy_assistant.store import IndexMismatch, Store

QS = load_questions()


@pytest.fixture(scope="session")
def e5():
    return LocalEmbedder()


@pytest.fixture(scope="session")
def retriever(tmp_path_factory, e5):
    store = Store(tmp_path_factory.mktemp("index") / "index.sqlite")
    store.sync(CORPUS / "documents", "structure", e5)
    return Retriever(store, e5)


def top(retriever, qid, method, k=3, **filters):
    q = QS[qid]
    f = Filters(as_of=filters.get("as_of", q.as_of), audience=filters.get("audience", "staff"))
    return [r.chunk for r in retriever.search(q.question, method, k, f)]


def test_the_model_and_its_revision(e5):
    assert (e5.name, e5.revision) == ("intfloat/multilingual-e5-small", "614241f622f53c4eeff9890bdc4f31cfecc418b3")
    assert e5.embed_queries(["warranty"]).shape == (1, 384)


def test_keywords_win_on_a_rare_identifier(retriever):
    """'What is LB-1?' (blade oil): BM25 finds it first; the vectors do not find it in the top 3."""
    assert top(retriever, "Q64", "bm25")[0].doc_id == "product-care-hedge-trimmer-ht550"
    assert all(c.doc_id != "product-care-hedge-trimmer-ht550" for c in top(retriever, "Q64", "dense"))


def test_vectors_win_on_a_french_question_about_english_documents(retriever):
    """'Puis-je retourner une carte-cadeau?': the answer is in English documents; no word in common."""
    answer_docs = {"gift-cards", "returns-policy"}
    assert not answer_docs & {c.doc_id for c in top(retriever, "Q63", "bm25")}
    assert answer_docs & {c.doc_id for c in top(retriever, "Q63", "dense")}


def test_vectors_win_on_a_paraphrase(retriever):
    """'garden sprinkler' is in the warranty table's Watering row; BM25 ranks it 16th, the vectors 2nd."""
    assert "warranty-policy" not in [c.doc_id for c in top(retriever, "Q34", "bm25", 5)]
    assert "warranty-policy" in [c.doc_id for c in top(retriever, "Q34", "dense", 3)]


def test_the_date_filter_chooses_the_version(retriever):
    assert {c.version for c in top(retriever, "Q22", "bm25", 10) if c.doc_id == "returns-policy"} == {"3"}
    assert {c.version for c in top(retriever, "Q22", "bm25", 10, as_of=None) if c.doc_id == "returns-policy"} == {"3", "4"}


def test_a_public_audience_never_gets_staff_chunks(retriever):
    for qid in ("Q49", "Q50", "Q51"):
        assert all(c.access == "public" for c in top(retriever, qid, "hybrid", 10, audience="public"))
    assert top(retriever, "Q51", "bm25", 1)[0].doc_id == "staff-discount-and-perks"   # staff do see it


def test_an_index_refuses_another_model(retriever):
    other = LocalEmbedder("sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
    with pytest.raises(IndexMismatch):
        Retriever(retriever.store, other).search("warranty", "dense")


def test_recorded_embed_small_vectors():
    small = RecordedEmbedder("embed-small")
    assert small.embed_queries([QS["Q01"].question]).shape == (1, 1536)
    with pytest.raises(RecordingNotFound):
        small.embed_queries(["a question that was never recorded"])
