from resolver.config import Settings, make_provider, redact
from resolver.providers import MockProvider


def test_the_key_is_never_printed(monkeypatch):
    monkeypatch.setenv("RESOLVER_API_KEY", "sk-test-1234567890abcdef")
    s = Settings.from_env()
    assert "sk-test" not in repr(s)
    assert "sk-test" not in redact("api_key=sk-test-1234567890abcdef")


def test_the_default_is_the_mock():
    assert isinstance(make_provider(Settings.from_env()), MockProvider)
