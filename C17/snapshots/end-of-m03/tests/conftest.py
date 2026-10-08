import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from escalation.bundle import bundle_digest

ROOT = Path(__file__).parent.parent
BUNDLE = ROOT / "bundles" / "escalation-1.0.0"

TICKET = {
    "ticket_id": "T-120001",
    "channel": "email",
    "team": "payment",
    "segment": "home",
    "region": "west",
    "priority": 1,
    "order_value": 89.5,
    "word_count": 112,
    "customer_tenure_days": 400,
    "prior_tickets_90d": 2,
    "created_hour": 10,
    "prior_escalations_90d": 1,
}


@pytest.fixture(autouse=True)
def settings_env(monkeypatch):
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("MODEL_BUNDLE", str(BUNDLE))
    monkeypatch.setenv("MODEL_SHA256", bundle_digest(BUNDLE))
    for name in ["API_KEY", "API_KEY_FILE", "REQUIRE_API_KEY", "SHADOW_BUNDLE", "SHADOW_SHA256"]:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def client():
    from escalation.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def ticket():
    return dict(TICKET)
