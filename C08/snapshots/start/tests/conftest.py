import pytest

from assistant.data import load_tickets
from assistant.providers import MockProvider


@pytest.fixture(autouse=True)
def use_the_mock(request, monkeypatch):
    """Tests always use the recorded answers, even when .env names a live provider (except `-m live`)."""
    if "live" not in request.keywords:
        monkeypatch.setenv("ASSISTANT_PROVIDER", "mock")
        monkeypatch.setenv("ASSISTANT_MODEL", "chat-small")


@pytest.fixture(scope="session")
def mock():
    return MockProvider()


@pytest.fixture(scope="session")
def tickets():
    return load_tickets()
