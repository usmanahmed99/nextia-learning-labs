"""Rate limits and timeouts are SIMULATED here (assistant/simulate.py): they are not provoked on a real provider."""
import random

import pytest

from assistant.providers import ProviderError, ProviderTimeout, RateLimited
from assistant.retry import RetryPolicy, backoff_s, call_with_retry
from assistant.simulate import SimulatedProvider


class Echo:
    def complete(self, request):
        return "answer"


def run(script, policy=RetryPolicy()):
    provider, waits = SimulatedProvider(Echo(), script), []
    result = call_with_retry(lambda: provider.complete({}), policy, sleep=waits.append, rng=random.Random(0))
    return result, waits, provider.calls


def test_a_rate_limit_waits_as_long_as_retry_after_says():
    result, waits, calls = run(["rate_limit:2", "ok"])
    assert (result, waits, calls) == ("answer", [2.0], 2)


def test_timeouts_and_server_errors_are_retried_with_growing_waits():
    policy = RetryPolicy(jitter=False)
    result, waits, calls = run(["timeout", "server_error", "timeout", "ok"], policy)
    assert result == "answer" and waits == [0.5, 1.0, 2.0] and calls == 4


def test_retries_stop_after_max_attempts():
    with pytest.raises(ProviderTimeout):
        run(["timeout"] * 10)


def test_a_bad_request_is_not_retried():
    class Bad:
        calls = 0

        def complete(self, request):
            self.calls += 1
            raise ProviderError("HTTP 400: bad request", status=400)

    bad = Bad()
    with pytest.raises(ProviderError):
        call_with_retry(lambda: bad.complete({}), sleep=lambda s: None)
    assert bad.calls == 1


def test_retries_stop_when_the_total_wait_would_be_too_long():
    with pytest.raises(RateLimited):
        run(["rate_limit:8", "rate_limit:8", "rate_limit:8", "ok"], RetryPolicy(max_total_s=10))


def test_backoff_doubles_up_to_the_cap_and_jitter_stays_below_it():
    policy, rng = RetryPolicy(jitter=False, base_s=0.5, cap_s=4), random.Random(1)
    assert [backoff_s(a, policy, rng) for a in range(1, 6)] == [0.5, 1, 2, 4, 4]
    jittered = RetryPolicy(base_s=0.5, cap_s=4)
    assert all(0 <= backoff_s(3, jittered, rng) <= 2 for _ in range(100))
