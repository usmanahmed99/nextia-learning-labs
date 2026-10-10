"""Failure containment for calls to the AI provider (the scaling course, Module 5).

- CircuitBreaker: after `failures` failures in a row, stop calling for `open_seconds`
  (the circuit is OPEN: calls fail at once, without waiting for a timeout). Then let one
  trial call through (HALF-OPEN): if it works, CLOSED again; if not, OPEN again.
- RetryBudget: retries may add at most `ratio` extra calls (10% by default) on top of
  the first attempts, counted over the last `window` seconds. During an outage almost
  every call fails; without a budget, every failure would become 2 or 3 calls and make the
  overload worse (a "retry storm").

Retry only what is safe to repeat. A call to the provider has no effect except its cost,
so it may be retried. A write is retried only with an idempotency key (Module 4).
"""

import time
from collections import deque


class BreakerOpen(Exception):
    """The circuit is open: the call was not made."""

    def __init__(self, retry_after: float):
        super().__init__(f"the circuit is open for {retry_after:.0f} more seconds")
        self.retry_after = retry_after


class CircuitBreaker:
    def __init__(self, failures: int = 5, open_seconds: float = 30.0, clock=time.monotonic):
        self.threshold = failures
        self.open_seconds = open_seconds
        self.clock = clock
        self.state = "closed"
        self.failures = 0
        self.opened_at = 0.0
        self.trial_running = False
        self.opened_count = 0

    def before_call(self) -> None:
        """Raises BreakerOpen if the call must not be made now."""
        if self.state == "open":
            waited = self.clock() - self.opened_at
            if waited < self.open_seconds:
                raise BreakerOpen(self.open_seconds - waited)
            self.state = "half_open"
            self.trial_running = False
        if self.state == "half_open":
            if self.trial_running:  # one trial at a time
                raise BreakerOpen(1.0)
            self.trial_running = True

    def success(self) -> None:
        self.state = "closed"
        self.failures = 0
        self.trial_running = False

    def failure(self) -> None:
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.threshold:
            if self.state != "open":
                self.opened_count += 1
            self.state = "open"
            self.opened_at = self.clock()
            self.trial_running = False


class RetryBudget:
    def __init__(
        self, ratio: float = 0.1, window: float = 10.0, minimum: int = 3, clock=time.monotonic
    ):
        self.ratio = ratio
        self.window = window
        self.minimum = minimum  # a few retries are always allowed (low traffic)
        self.clock = clock
        self.calls: deque[float] = deque()
        self.retries: deque[float] = deque()
        self.refused = 0

    def _trim(self) -> None:
        old = self.clock() - self.window
        for q in (self.calls, self.retries):
            while q and q[0] < old:
                q.popleft()

    def record_call(self) -> None:
        self.calls.append(self.clock())

    def can_retry(self) -> bool:
        self._trim()
        if len(self.retries) < max(self.minimum, self.ratio * len(self.calls)):
            self.retries.append(self.clock())
            return True
        self.refused += 1
        return False
