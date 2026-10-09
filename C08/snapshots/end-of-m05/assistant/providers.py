"""The adapter: the only code that talks to a model provider.

The rest of the assistant builds a request (a dict in the Chat Completions format) and gets back a
`Completion`. Two providers do the work:

- MockProvider replays responses that were recorded for the course. No account, no network.
- OpenAICompatibleProvider calls any server that speaks the OpenAI-compatible Chat Completions API:
  a local Ollama server, OpenAI, or another provider. Its settings come from environment variables.
"""

import contextlib
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"
KEY_FIELDS = ("model", "messages", "response_format", "tools", "max_completion_tokens", "stream")


class ProviderError(Exception):
    """The provider could not give an answer."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ProviderTimeout(ProviderError):
    """No complete answer within the timeout."""


class RateLimited(ProviderError):
    """HTTP 429: too many requests. `retry_after` is the wait in seconds that the provider asked for."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message, status=429)
        self.retry_after = retry_after


class RecordingNotFound(ProviderError):
    """The mock has no recorded response for this exact request."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text written by the model: not yet checked


@dataclass
class Completion:
    text: str | None
    finish_reason: str
    refusal: str | None
    tool_calls: list[ToolCall]
    model: str
    request_id: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_s: float
    raw: dict = field(repr=False)

    @classmethod
    def from_response(cls, data: dict, latency_s: float) -> "Completion":
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        calls = [ToolCall(c["id"], c["function"]["name"], c["function"]["arguments"])
                 for c in message.get("tool_calls") or []]
        return cls(
            text=message.get("content"),
            finish_reason=choice.get("finish_reason") or "",
            refusal=message.get("refusal"),
            tool_calls=calls,
            model=data.get("model", ""),
            request_id=data.get("id", ""),
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            reasoning_tokens=details.get("reasoning_tokens") or 0,
            latency_s=latency_s,
            raw=data,
        )


def request_key(request: dict) -> str:
    """A stable name for a request: the same fields in, the same key out."""
    fields = {name: request.get(name) for name in KEY_FIELDS}
    text = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class MockProvider:
    """Replays recorded responses. A request that was not recorded raises RecordingNotFound."""

    def __init__(self, folder: Path = RECORDINGS, speed: float = 0.0):
        self.speed = speed  # 1.0 replays a stream with its recorded timing; 0 replays it at once
        self.recordings = {}
        for path in sorted(folder.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                self.recordings[entry["key"]] = entry

    def _entry(self, request: dict) -> dict:
        key = request_key(request)
        if key not in self.recordings:
            raise RecordingNotFound(
                f"No recording for this request (key {key}). The mock replays only the requests that were "
                "recorded for the course: check the ticket ID, the prompt version and the model.")
        entry = self.recordings[key]
        if "error" in entry:
            error = entry["error"]
            raise ProviderError(f"HTTP {error['status']}: {error['message']}", status=error["status"])
        return entry

    def complete(self, request: dict) -> Completion:
        entry = self._entry(request)
        return Completion.from_response(entry["response"], entry["latency_s"])

    def stream(self, request: dict) -> Iterator[tuple[float, str]]:
        """Yield (seconds since the request, text piece) as the recorded stream did."""
        entry = self._entry({**request, "stream": True})
        start = time.monotonic()
        for at, piece in entry["chunks"]:
            if self.speed:
                time.sleep(max(0.0, at / self.speed - (time.monotonic() - start)))
            yield at, piece


@contextlib.contextmanager
def translate_errors():
    """Turn the SDK's exceptions into the assistant's own, so that no other file imports `openai`."""
    import openai

    try:
        yield
    except openai.APITimeoutError as e:
        raise ProviderTimeout("The provider did not answer within the timeout.") from e
    except openai.RateLimitError as e:
        wait = e.response.headers.get("retry-after")
        raise RateLimited("HTTP 429: rate limited.", float(wait) if wait else None) from e
    except openai.APIStatusError as e:
        raise ProviderError(f"HTTP {e.status_code}: {e.message}", status=e.status_code) from e
    except openai.APIConnectionError as e:
        raise ProviderError("Cannot reach the provider (connection error).") from e


class OpenAICompatibleProvider:
    """Calls a server that speaks the OpenAI-compatible Chat Completions API."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 30.0):
        from openai import OpenAI  # imported here, so that the mock works without a network library set up

        # max_retries=0: the assistant decides about retries itself (retry.py).
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed", timeout=timeout_s, max_retries=0)

    def complete(self, request: dict) -> Completion:
        start = time.monotonic()
        with translate_errors():
            response = self.client.chat.completions.create(**request)
        return Completion.from_response(response.model_dump(), round(time.monotonic() - start, 3))

    def stream(self, request: dict) -> Iterator[tuple[float, str]]:
        start = time.monotonic()
        with translate_errors():
            for chunk in self.client.chat.completions.create(**request, stream=True):
                if chunk.choices and chunk.choices[0].delta.content:
                    yield round(time.monotonic() - start, 3), chunk.choices[0].delta.content
