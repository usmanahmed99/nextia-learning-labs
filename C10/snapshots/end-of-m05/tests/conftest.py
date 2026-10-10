import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
# The tests never touch your practice database or your saved runs: they work in a temporary folder.
os.environ["RESOLVER_WORK"] = tempfile.mkdtemp(prefix="resolver-tests-")


@pytest.fixture(autouse=True)
def mock_provider(monkeypatch):
    """Tests never call a real provider and never read a key, whatever .env says (except `pytest -m live`)."""
    if os.environ.get("PYTEST_LIVE") == "1":
        return
    monkeypatch.setenv("RESOLVER_PROVIDER", "mock")
    monkeypatch.setenv("RESOLVER_MODEL", "chat-small")
    monkeypatch.delenv("RESOLVER_API_KEY", raising=False)


@pytest.fixture
def world(tmp_path):
    """A fresh practice database for one test."""
    import shutil

    from resolver.data import SEED_DB
    from resolver.systems import World

    db = tmp_path / "larkfield.sqlite"
    shutil.copyfile(SEED_DB, db)
    return lambda ticket_id="T-TEST", faults=None: World(db, ticket_id, faults)
