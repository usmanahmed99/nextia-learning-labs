"""The adapter of the optional live judge: the mock, and the usage cap in code."""

import pytest

from harness.config import Settings, make_provider
from harness.providers import CappedProvider, Completion, MockProvider, RecordingNotFound, UsageCapReached


class FakeLive:
    def __init__(self):
        self.calls = 0

    def complete(self, request):
        self.calls += 1
        return Completion("{}", "stop", "fake", 1000, 200, 0.1, {})


def test_the_cap_stops_before_the_call():
    live = FakeLive()
    capped = CappedProvider(live, max_calls=3, max_tokens=10_000)
    for _ in range(3):
        capped.complete({})
    with pytest.raises(UsageCapReached, match="Nothing was sent"):
        capped.complete({})
    assert live.calls == 3


def test_the_token_cap():
    capped = CappedProvider(FakeLive(), max_calls=100, max_tokens=2_000)
    capped.complete({})
    capped.complete({})  # 2,400 tokens used now
    with pytest.raises(UsageCapReached):
        capped.complete({})


def test_the_key_is_never_printed(monkeypatch):
    monkeypatch.setenv("JUDGE_API_KEY", "sk-test-not-a-real-key")
    assert "sk-test" not in repr(Settings.from_env())


def test_mock_by_default():
    assert isinstance(make_provider(Settings.from_env()), MockProvider)


def test_an_unrecorded_request_is_refused():
    with pytest.raises(RecordingNotFound, match="No recording"):
        MockProvider().complete({"model": "chat-strong", "messages": [{"role": "user", "content": "hello"}]})
