"""Opt-in live evaluation: `python -m pytest -m live`. Needs a live provider in .env (Ollama is free).

It checks the plumbing on 5 fixed tickets (an answer comes back and goes through both gates), and prints
the score. It does not fail on a wrong team: quality is measured with `python -m assistant eval`.
"""
import pytest

from assistant.analyse import analyse_ticket
from assistant.config import Settings, make_provider
from assistant.data import load_tickets

pytestmark = pytest.mark.live
LIVE_SET = ["T-80008", "T-80004", "T-80001", "T-80005", "T-64917"]


@pytest.fixture(scope="module")
def live():
    settings = Settings.from_env()
    if settings.provider == "mock":
        pytest.skip("No live provider: set ASSISTANT_PROVIDER=openai_compatible in .env (see .env.example).")
    return settings, make_provider(settings)


def test_live_evaluation_set(live, capsys):
    settings, provider = live
    tickets = load_tickets()
    outcomes = [analyse_ticket(tickets[t], provider, settings.model, tools=False,
                               reasoning_effort=settings.reasoning_effort) for t in LIVE_SET]
    assert all(o.status in ("valid", "rejected") for o in outcomes), [o.error for o in outcomes]
    right = sum(1 for o in outcomes if o.analysis and o.analysis.team == tickets[o.ticket_id].team)
    with capsys.disabled():
        print(f"\nlive: {settings.model}: team right {right}/5, valid {sum(o.status == 'valid' for o in outcomes)}/5")
