"""Secrets and logs: a secret is loaded only by the code that needs it and never printed; the audit log
is redacted; a blocked operation leaves a useful audit event with no secret and no message text."""

from support_assistant.config import Settings, load_service_env, redact
from support_assistant.data import made_up_secrets
from support_assistant.runner import fresh_world
from tests._helpers import SECURE, run, session


def test_redact_removes_keys_and_tokens():
    secret = made_up_secrets()[0]
    text = f"key={secret} Authorization: Bearer abcdefghijkl api_key: 'xyz123456'"
    out = redact(text)
    assert secret not in out and "abcdefghijkl" not in out and "xyz123456" not in out


def test_the_settings_never_show_the_api_key():
    s = Settings(provider="openai_compatible", api_key="sk-made-up-123456")
    assert "sk-made-up-123456" not in repr(s)


def test_the_secrets_loader_returns_the_value_without_printing_it(capsys):
    value = load_service_env("PAYMENTS_API_KEY")
    assert value in made_up_secrets()
    assert capsys.readouterr().out == ""


def test_a_blocked_operation_writes_a_redacted_audit_event():
    w = fresh_world()
    t = w.ticket("T-24110")
    run("read_file", {"path": "../config/service.env"}, SECURE, session(), t, w)
    run("fetch_url", {"url": "http://169.254.169.254/latest/meta-data/"}, SECURE, session(), t, w)
    blocked = [e for e in w.audit_rows() if e["result"] == "blocked"]
    assert [e["action"] for e in blocked] == ["read_file", "fetch_url"]
    assert blocked[1]["detail"]["host"] == "169.254.169.254"
    text = str(blocked)
    assert not any(s in text for s in made_up_secrets())
