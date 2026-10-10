"""The adapter for the optional live judge: the only code that talks to a model provider.

From the LLM applications course, trimmed (no tools, no streaming):
- MockProvider replays the judgments recorded for the course (recordings/judge_*.jsonl). The default.
- OpenAICompatibleProvider calls any server that speaks the OpenAI-compatible Chat Completions API:
  a local Ollama server, OpenAI, or another provider.
- CappedProvider wraps a live provider and stops after a fixed number of calls and tokens, so that a
  mistake in a loop cannot spend money.
"""

import email.utils
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"
KEY_FIELDS = ("model", "messages", "response_format", "tools", "max_completion_tokens", "stream")


class ProviderError(Exception):
    """The provider could not give an answer."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class RecordingNotFound(ProviderError):
    """The mock has no recorded response for this exact request."""


class UsageCapReached(ProviderError):
    """The live judge used its whole budget of calls or tokens."""


@dataclass
class Completion:
    text: str | None
    finish_reason: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    raw: dict = field(repr=False)

    @classmethod
    def from_response(cls, data: dict, latency_s: float) -> "Completion":
        choice = data["choices"][0]
        usage = data.get("usage") or {}
        return cls(text=choice["message"].get("content"), finish_reason=choice.get("finish_reason") or "",
                   model=data.get("model", ""), input_tokens=usage.get("prompt_tokens", 0),
                   output_tokens=usage.get("completion_tokens", 0), latency_s=latency_s, raw=data)


def request_key(request: dict) -> str:
    """A stable name for a request: the same fields in, the same key out."""
    fields = {name: request.get(name) for name in KEY_FIELDS}
    text = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class MockProvider:
    """Replays recorded responses. A request that was not recorded raises RecordingNotFound."""

    def __init__(self, folder: Path = RECORDINGS):
        self.recordings = {}
        for path in sorted(folder.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.recordings[entry["key"]] = entry

    def complete(self, request: dict) -> Completion:
        key = request_key(request)
        if key not in self.recordings:
            raise RecordingNotFound(
                f"No recording for this request (key {key}). The mock replays only the judgments recorded for the "
                "course: check the case, the run, the judge model and the prompt version.")
        entry = self.recordings[key]
        if "error" in entry:
            raise ProviderError(f"HTTP {entry['error']['status']}: {entry['error']['message']}", entry["error"]["status"])
        return Completion.from_response(entry["response"], entry["latency_s"])


def retry_after_s(headers) -> float | None:
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        value = headers.get(name)
        if value is None:
            continue
        try:
            return max(0.0, float(value) * scale)
        except ValueError:
            pass
        try:
            return max(0.0, (email.utils.parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            pass
    return None


class OpenAICompatibleProvider:
    """Calls a server that speaks the OpenAI-compatible Chat Completions API."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0):
        from openai import OpenAI  # imported here, so that the mock works without the package set up

        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed", timeout=timeout_s, max_retries=0)

    def complete(self, request: dict) -> Completion:
        import openai

        start = time.monotonic()
        try:
            response = self.client.chat.completions.create(**request)
        except openai.APIStatusError as e:
            raise ProviderError(f"HTTP {e.status_code}: {e.message}", status=e.status_code) from e
        except openai.APIConnectionError as e:
            raise ProviderError("Cannot reach the provider (connection error).") from e
        return Completion.from_response(response.model_dump(), round(time.monotonic() - start, 3))


class CappedProvider:
    """A live provider with a hard budget. The check happens before each call."""

    def __init__(self, inner, max_calls: int = 20, max_tokens: int = 60_000):
        self.inner, self.max_calls, self.max_tokens = inner, max_calls, max_tokens
        self.calls = self.tokens = 0

    def complete(self, request: dict) -> Completion:
        if self.calls >= self.max_calls or self.tokens >= self.max_tokens:
            raise UsageCapReached(f"Usage cap reached: {self.calls} calls, {self.tokens} tokens "
                                  f"(limits {self.max_calls} calls, {self.max_tokens} tokens). Nothing was sent.")
        self.calls += 1
        completion = self.inner.complete(request)
        self.tokens += completion.input_tokens + completion.output_tokens
        return completion
