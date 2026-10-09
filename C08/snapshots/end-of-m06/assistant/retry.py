"""Retry what is safe to repeat, with bounded exponential backoff and jitter.

Analysing a ticket only reads: repeating the request changes nothing, so it is safe to retry.
A request with side effects (a refund, a message to a customer) is not retried without an idempotency key.
"""

import random
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

from .providers import ProviderError, ProviderTimeout, RateLimited

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 4      # the first call and up to 3 retries
    base_s: float = 0.5        # the first wait before jitter
    cap_s: float = 8.0         # no single wait is longer than this
    jitter: bool = True        # a random wait between 0 and the backoff, so that clients do not retry together
    max_total_s: float = 20.0  # stop when the waits would add up to more than this


def is_retryable(error: Exception) -> bool:
    if isinstance(error, (RateLimited, ProviderTimeout)):
        return True
    return isinstance(error, ProviderError) and error.status is not None and error.status >= 500


def backoff_s(attempt: int, policy: RetryPolicy, rng: random.Random) -> float:
    """The wait after failed attempt number `attempt` (1, 2, 3 ...): base x 2^(attempt-1), capped, then jitter."""
    wait = min(policy.cap_s, policy.base_s * 2 ** (attempt - 1))
    return rng.uniform(0, wait) if policy.jitter else wait


def call_with_retry(call: Callable[[], T], policy: RetryPolicy = RetryPolicy(),
                    sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None,
                    on_retry: Callable[[int, Exception, float], None] | None = None) -> T:
    rng = rng or random.Random()
    waited = 0.0
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return call()
        except ProviderError as error:
            if not is_retryable(error) or attempt == policy.max_attempts:
                raise
            wait = backoff_s(attempt, policy, rng)
            if isinstance(error, RateLimited) and error.retry_after is not None:
                wait = min(error.retry_after, policy.cap_s)  # the provider said how long to wait
            if waited + wait > policy.max_total_s:
                raise
            if on_retry:
                on_retry(attempt, error, wait)
            sleep(wait)
            waited += wait
    raise AssertionError("unreachable")
