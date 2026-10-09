import pytest

from assistant.data import load_tickets
from assistant.providers import MockProvider


@pytest.fixture(autouse=True)
def use_the_mock(request, monkeypatch):
    """Tests always use the recorded answers, even when .env names a live provider (except `-m live`)."""
    if "live" not in request.keywords:
        monkeypatch.setenv("ASSISTANT_PROVIDER", "mock")
        monkeypatch.setenv("ASSISTANT_MODEL", "chat-small")


@pytest.fixture(autouse=True)
def keep_the_usage_log_clean(tmp_path, monkeypatch):
    """A test run must not add lines to your real logs/usage.jsonl."""
    monkeypatch.setattr("assistant.usage.LOG_FILE", tmp_path / "usage.jsonl")


@pytest.fixture(scope="session")
def mock():
    return MockProvider()


@pytest.fixture(scope="session")
def tickets():
    return load_tickets()
