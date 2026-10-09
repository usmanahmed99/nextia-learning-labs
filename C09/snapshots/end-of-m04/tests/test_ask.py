"""The whole pipeline with the mock provider: search -> context -> recorded answer -> citation check.

The mock finds a recording only if the request is exactly the recorded one: the same question, the same
passages in the same order, the same prompt and model. So this test also checks that search and context
give, on your computer, exactly what they gave when the answers were recorded.
"""

import re

import pytest

from policy_assistant.assistant import ask
from policy_assistant.documents import CORPUS
from policy_assistant.embed import LocalEmbedder
from policy_assistant.evaluate import load_questions
from policy_assistant.providers import MockProvider
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


def test_the_documents_do_not_answer(retriever):
    q = QS["Q14"]   # a student discount
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "rerank")
    assert result.answer.answerable is False and result.answer.claims == ()


def test_the_weak_retrieval_replays_too(retriever):
    q = QS["Q34"]   # a garden sprinkler: BM25 misses the warranty table
    result = ask(q.question, q.as_of, retriever, MockProvider(), "chat-small", "bm25")
    assert "warranty-policy" not in {c.doc_id for c in result.context.chunks}
    assert not correct(q, result.answer)
