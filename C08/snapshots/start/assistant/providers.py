"""The adapter: the only code that talks to a model provider.

The rest of the assistant builds a request (a dict in the Chat Completions format) and gets back a
`Completion`. For now there is one provider:

- MockProvider replays responses that were recorded for the course. No account, no network.
"""

import hashlib
import json
from dataclasses import dataclass, field
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

    def __init__(self, folder: Path = RECORDINGS):
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
