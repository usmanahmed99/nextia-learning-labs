from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
BUNDLE = ROOT / "bundles" / "escalation-1.0.0"

# The example ticket of contract.py. Each test changes one thing in a copy.
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


@pytest.fixture
def ticket():
    return dict(TICKET)
