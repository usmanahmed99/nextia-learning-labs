"""A SIMULATED provider for tests and demonstrations: it fails on purpose, in a fixed order.

Real rate limits and outages are not provoked for the course. This wrapper raises the same errors that
OpenAICompatibleProvider raises for a real HTTP 429, timeout or 5xx, then lets the next call through.
"""

from .providers import Completion, ProviderError, ProviderTimeout, RateLimited


class SimulatedProvider:
    def __init__(self, inner, script: list[str]):
        """script: one item per call, for example ["rate_limit:2", "timeout", "ok"].
        "rate_limit:N" = HTTP 429 with Retry-After N seconds ("rate_limit" alone has no Retry-After),
        "timeout", "server_error" (HTTP 503), "ok" = ask the inner provider. After the script: always "ok"."""
        self.inner = inner
        self.script = list(script)
        self.calls = 0

    def complete(self, request: dict) -> Completion:
        self.calls += 1
        step = self.script.pop(0) if self.script else "ok"
        if step.startswith("rate_limit"):
            wait = step.partition(":")[2]
            raise RateLimited("HTTP 429: rate limited (simulated).", float(wait) if wait else None)
        if step == "timeout":
            raise ProviderTimeout("The provider did not answer within the timeout (simulated).")
        if step == "server_error":
            raise ProviderError("HTTP 503: service unavailable (simulated).", status=503)
        return self.inner.complete(request)
