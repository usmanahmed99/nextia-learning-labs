"""Shared test helpers. The tests never touch the network outside 127.0.0.1 and never need a key."""

import socket
import threading
import time

import pytest
import uvicorn

from support_mcp.knowledge import Knowledge


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Each test gets its own proposals database and identity provider key folder."""
    monkeypatch.setenv("SUPPORT_STATE", str(tmp_path / "state.db"))
    monkeypatch.setenv("IDP_DIR", str(tmp_path / "idp"))
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


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Served:
    """An ASGI app served by uvicorn in a thread, on a free port of 127.0.0.1."""

    def __init__(self, app, port: int):
        self.port = port
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        deadline = time.time() + 10
        while not self.server.started and time.time() < deadline:
            time.sleep(0.02)
        return self

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)
