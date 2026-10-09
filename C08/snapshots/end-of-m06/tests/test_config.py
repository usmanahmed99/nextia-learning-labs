import pytest

from assistant.config import Settings, make_provider, redact
from assistant.providers import MockProvider


def test_printing_the_settings_never_shows_the_key():
    settings = Settings(provider="openai_compatible", api_key="sk-test-1234567890abcdef")
    assert "sk-test" not in repr(settings)


def test_the_default_provider_is_the_mock(monkeypatch):
    for name in ("ASSISTANT_PROVIDER", "ASSISTANT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("assistant.config.ENV_FILE", __import__("pathlib").Path("/nonexistent/.env"))
    assert isinstance(make_provider(Settings.from_env()), MockProvider)


def test_a_live_provider_needs_a_base_url():
    with pytest.raises(ValueError, match="ASSISTANT_BASE_URL"):
        make_provider(Settings(provider="openai_compatible"))


@pytest.mark.parametrize("text, secret", [
    ("Authorization: Bearer abcdefgh12345678", "abcdefgh12345678"),
    ('{"api-key": "0123456789abcdef0123"}', "0123456789abcdef0123"),
    ("key sk-proj-AbCdEf123456789", "sk-proj-AbCdEf123456789"),
    ("card 4111 1111 1111 1111 declined", "4111 1111 1111 1111"),
    ("write to helen.brooks@example.com", "helen.brooks@example.com"),
])
def test_redact_hides_secrets(text, secret):
    assert secret not in redact(text)


def test_redact_keeps_order_ids():
    assert redact("order LK-714258") == "order LK-714258"
