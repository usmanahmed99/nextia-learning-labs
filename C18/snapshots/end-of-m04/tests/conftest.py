from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from ticket_api.config import Settings
from ticket_api.main import create_app

TEST_SETTINGS = Settings(
    api_key=None,
    allowed_origins=[],
    classifier_mode="keywords",
    classifier_timeout=2.0,
    log_level="WARNING",
    show_docs=True,
)


@pytest.fixture
def make_client():
    """Return a function that makes a test client with changed settings."""

    def make(**changes) -> TestClient:
        app = create_app(replace(TEST_SETTINGS, **changes))
        return TestClient(app, raise_server_exceptions=False)

    return make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()
