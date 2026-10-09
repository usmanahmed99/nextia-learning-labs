import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch):
    """Tests never call a real provider and never read a key, whatever .env says (except `pytest -m live`)."""
    if os.environ.get("PYTEST_LIVE") == "1":
        return
    monkeypatch.setenv("ASSISTANT_PROVIDER", "mock")
    monkeypatch.delenv("ASSISTANT_API_KEY", raising=False)
