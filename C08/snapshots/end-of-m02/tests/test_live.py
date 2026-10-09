"""Opt-in live check: `python -m pytest -m live`. Needs a live provider in .env (Ollama is free)."""
import pytest

from assistant.config import Settings, make_provider
from assistant.context import build_request
from assistant.data import load_ticket

pytestmark = pytest.mark.live


def test_one_live_request():
    settings = Settings.from_env()
    if settings.provider == "mock":
        pytest.skip("No live provider: set ASSISTANT_PROVIDER=openai_compatible in .env (see .env.example).")
    completion = make_provider(settings).complete(build_request(load_ticket("T-80008"), settings.model, "v1"))
    assert completion.text and completion.input_tokens > 0
