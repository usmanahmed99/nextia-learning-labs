"""The whole pipeline with the mock provider: search -> context -> recorded answer -> citation check.

The mock replays the recording of the same question, prompt and model. With exactly the recorded passages
it replays silently (so these tests also check that search and context give, on your computer, what they
gave when the answers were recorded); with other passages it still replays, with a note.
"""

import re

import pytest

from policy_assistant.assistant import ask
from policy_assistant.documents import CORPUS
from policy_assistant.embed import LocalEmbedder
from policy_assistant.evaluate import load_questions
from policy_assistant.providers import MockProvider, RecordingNotFound
from policy_assistant.rerank import Reranker
from policy_assistant.search import Retriever
from policy_assistant.store import Store

QS = load_questions()


def correct(q, answer) -> bool:
    """The question's keys all match and no must_not matches (Module 5 turns this into evaluate.answer_scores)."""
    text = answer.text()
    return all(re.search(k, text, re.I) for k in q.keys) and not any(re.search(m, text, re.I) for m in q.must_not)


@pytest.fixture(scope="module")
def retriever(tmp_path_factory):
    e5 = LocalEmbedder()
    store = Store(tmp_path_factory.mktemp("ask") / "index.sqlite")
    store.sync(CORPUS / "documents", "structure", e5)
    return Retriever(store, e5, Reranker())


@pytest.mark.parametrize("qid", ["Q22", "Q24", "Q38", "Q14"])
def test_recorded_answers_replay(retriever, qid):
    q = QS[qid]
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "rerank", language=q.language)
    assert result.answer is not None, result.problem
    assert correct(q, result.answer) if not q.abstain else not result.answer.answerable
    assert all(i in result.context.ids for c in result.answer.claims for i in c.chunk_ids)
    assert result.completion.note == ""          # exactly the recorded passages: no warning


def test_other_passages_replay_with_a_warning(retriever):
    """Dense search finds other passages than the recorded (rerank) ones: the answer is replayed, the note says
    so, and the citation checks run against the passages that this search really gave."""
    q = QS["Q22"]
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "dense", language=q.language)
    assert result.answer is not None and correct(q, result.answer)
    assert result.completion.note.startswith("Recorded with passages ")
    assert "; yours: " + ", ".join(result.context.ids) in result.completion.note
    for check in result.checks:                  # a recorded citation outside your passages is reported, others not
        outside = [i for i in check.chunk_ids if i not in result.context.ids]
        assert [p for p in check.problems if p.startswith("not_in_context")] == [f"not_in_context:{i}" for i in outside]


def test_a_question_that_was_not_recorded(retriever):
    with pytest.raises(RecordingNotFound):
        MockProvider().complete({"model": "chat-small", "messages": [
            {"role": "user", "content": "Question date: 2026-10-09\nQuestion: Is this recorded?\n\nPassages:\n"}]})


def test_the_documents_do_not_answer(retriever):
    q = QS["Q14"]   # a student discount
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "rerank")
    assert result.answer.answerable is False and result.answer.claims == ()


def test_the_weak_retrieval_replays_too(retriever):
    q = QS["Q34"]   # a garden sprinkler: BM25 misses the warranty table
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "bm25")
    assert "warranty-policy" not in {c.doc_id for c in result.context.chunks}
    assert not correct(q, result.answer)
