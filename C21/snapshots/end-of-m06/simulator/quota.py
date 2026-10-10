"""The provider's quota: requests per minute and tokens per minute, as two token buckets.

A real provider checks its quota over short windows, so a burst is refused before a
minute's worth of requests has arrived. Here each bucket holds `burst_seconds` worth of
the per-minute limit and refills continuously. A refused request gets HTTP 429. Like the recorded
provider, the answer has two hints: `retry-after-ms` (when the bucket has room again)
and `Retry-After` (a fixed 30 seconds, as the real provider sent every time).
"""

import time


class Bucket:
    def __init__(self, per_minute: float, burst_seconds: float, clock=time.monotonic):
        self.rate = per_minute / 60.0
        self.capacity = max(1.0, self.rate * burst_seconds)
        self.level = self.capacity
        self.clock = clock
        self.updated = clock()

    def _refill(self) -> None:
        now = self.clock()
        self.level = min(self.capacity, self.level + (now - self.updated) * self.rate)
        self.updated = now

    def wait_for(self, amount: float) -> float:
        """Seconds until `amount` fits (0 if it fits now)."""
        self._refill()
        if self.level >= amount:
            return 0.0
        return (min(amount, self.capacity) - self.level) / self.rate

    def take(self, amount: float) -> None:
        self._refill()
        self.level -= amount


class Quota:
    def __init__(
        self, rpm: float | None, tpm: float | None, burst_seconds: float, clock=time.monotonic
    ):
        self.requests = Bucket(rpm, burst_seconds, clock) if rpm else None
        self.tokens = Bucket(tpm, burst_seconds, clock) if tpm else None

    def try_take(self, tokens: int) -> float | None:
        """None if the request may run now; otherwise the seconds until it would fit."""
        waits = []
        if self.requests is not None:
            waits.append(self.requests.wait_for(1))
        if self.tokens is not None:
            waits.append(self.tokens.wait_for(tokens))
        wait = max(waits, default=0.0)
        if wait > 0:
            return wait
        if self.requests is not None:
            self.requests.take(1)
        if self.tokens is not None:
            self.tokens.take(tokens)
        return None
