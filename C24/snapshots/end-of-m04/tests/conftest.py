import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
os.environ["ASSISTANT_WORK"] = tempfile.mkdtemp(prefix="c24-tests-")


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    if os.environ.get("PYTEST_LIVE") == "1":
        return
    monkeypatch.setenv("ASSISTANT_PROVIDER", "mock")
    monkeypatch.setenv("ASSISTANT_MODEL", "chat-small")
    monkeypatch.delenv("ASSISTANT_API_KEY", raising=False)


@pytest.fixture
def world():
    from support_assistant.runner import fresh_world
    return fresh_world
