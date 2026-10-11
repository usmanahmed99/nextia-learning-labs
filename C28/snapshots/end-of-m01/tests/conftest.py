"""Shared test helpers. The tests never touch the network outside 127.0.0.1 and never need a key."""

import pytest

from support_mcp.knowledge import Knowledge


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Each test starts with no practice switches set."""
    monkeypatch.delenv("SUPPORT_SLOW_SECONDS", raising=False)


@pytest.fixture(scope="session")
def knowledge():
    return Knowledge()


@pytest.fixture
def as_user(monkeypatch):
    """Set who starts the local server: as_user("usr-sam", "larkfield", "knowledge:read tickets:read")."""

    def set_user(user="usr-sam", tenant="larkfield", scopes="knowledge:read tickets:read"):
        monkeypatch.setenv("SUPPORT_USER", user)
        monkeypatch.setenv("SUPPORT_TENANT", tenant)
        monkeypatch.setenv("SUPPORT_SCOPES", scopes)

    set_user()
    return set_user
