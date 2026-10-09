"""Opt-in: ask a live model (Ollama or your own key). Skipped unless you run `pytest -m live` with
ASSISTANT_PROVIDER=openai_compatible and ASSISTANT_BASE_URL (and ASSISTANT_MODEL) set in .env."""

import os

import pytest

pytestmark = pytest.mark.live


@pytest.fixture(autouse=True)
def mock_provider():   # replaces conftest's fixture: this test must reach the live provider
    os.environ["PYTEST_LIVE"] = "1"
    yield
    os.environ.pop("PYTEST_LIVE", None)


def test_live_answer_cites_passages(tmp_path):
    from policy_assistant.assistant import ask
    from policy_assistant.config import Settings, make_provider
    from policy_assistant.documents import CORPUS
    from policy_assistant.embed import LocalEmbedder
    from policy_assistant.search import Retriever
    from policy_assistant.store import Store

    settings = Settings.from_env()
    if settings.provider != "openai_compatible":
        pytest.skip("Set ASSISTANT_PROVIDER=openai_compatible to run the live test.")
    e5 = LocalEmbedder()
    store = Store(tmp_path / "index.sqlite")
    store.sync(CORPUS / "documents", "structure", e5)
    result = ask("What is the return window for unused items?", "2026-10-09", Retriever(store, e5),
                 make_provider(settings), settings.model, method="hybrid")
    assert result.answer is not None, result.problem
    assert all(i in result.context.ids for c in result.answer.claims for i in c.chunk_ids) or result.checks
