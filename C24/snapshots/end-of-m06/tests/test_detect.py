"""Detection: the rules raise an alert for a pattern, not for one event, and an alert carries no
message text."""

from support_assistant.config import Settings, make_provider
from support_assistant.data import load_attacks, made_up_secrets
from support_assistant.detect import alerts, flatten
from support_assistant.runner import fresh_world, run_and_score


def _events(design, cases):
    complete = make_provider(Settings(provider="mock")).complete
    events = []
    for c in cases:
        w = fresh_world(redact_log=(design != "start"))
        run_and_score(c, complete, "chat-small", design, world=w)
        events += flatten(w.audit_rows())
    return events


def test_an_ssrf_attempt_raises_a_high_alert_with_no_content():
    attacks = load_attacks()
    found = alerts(_events("secure", [attacks[c] for c in ("ATK-22", "ATK-35", "ATK-36")]))
    high = [a for a in found if a["rule"] == "private_address"]
    assert high and high[0]["severity"] == "high"
    text = str(found)
    assert not any(s in text for s in made_up_secrets())


def test_one_blocked_read_is_not_an_alert_but_a_pattern_is():
    one = [{"run": "R-1", "actor": "usr-sam", "tenant": "larkfield", "action": "read_file", "result": "blocked",
            "code": "file_denied"}]
    assert alerts(one) == []
    many = [{**one[0], "run": f"R-{i}"} for i in range(3)]
    assert [a["rule"] for a in alerts(many)] == ["blocked_tools"]
