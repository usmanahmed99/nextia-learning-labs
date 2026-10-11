"""Credential boundaries: each part gets only the credentials it needs (Module 6)."""

import subprocess
import sys

from mcp.client.stdio import get_default_environment

from host import app

PROBE = "import os; print('MODEL_API_KEY' in os.environ, os.environ.get('SUPPORT_STATE', ''))"


def test_the_local_server_never_gets_the_model_key(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "practice-not-a-real-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.invalid/v1")
    params = app.server_params("usr-sam", "larkfield")
    assert "MODEL_API_KEY" not in params.env and "MODEL_BASE_URL" not in params.env
    # Start a child the way the SDK starts the server (mcp/client/stdio.py merges the same way).
    env = get_default_environment() | params.env
    out = subprocess.run([sys.executable, "-c", PROBE], env=env, capture_output=True, text=True).stdout.split()
    assert out[0] == "False"


def test_the_local_server_still_gets_its_own_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPPORT_STATE", str(tmp_path / "s.db"))
    env = app.server_params("usr-omar", "larkfield", "knowledge:read").env
    assert env["SUPPORT_USER"] == "usr-omar" and env["SUPPORT_TENANT"] == "larkfield"
    assert env["SUPPORT_SCOPES"] == "knowledge:read" and env["SUPPORT_STATE"] == str(tmp_path / "s.db")
