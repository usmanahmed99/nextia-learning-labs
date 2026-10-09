"""The adapter: the only code that talks to a chat model (the pattern of the LLM applications course).

The rest of the assistant builds a request (a dict in the Chat Completions format) and gets back a
`Completion`. Two providers:

- MockProvider replays responses that were recorded for the course. No account, no network.
- OpenAICompatibleProvider calls any server that speaks the OpenAI-compatible Chat Completions API:
  a local Ollama server, OpenAI, or another provider. Its settings come from environment variables.

How the mock finds a recording:
1. `request_key`: a hash of the model, the messages, the response format and the token limit. The
   same request as the recorded one (the same passages too) replays silently.
2. Otherwise `replay_key`: the same hash with the passages left out of the user message, so the
   model, the prompt (its system message and template), the question and its date must match. If
   your search found other passages than the recorded ones, the mock still replays the recording
   whose passages overlap most with yours, and `Completion.note` says so: "Recorded with passages
   ...; yours: ...". The citation checks then run against YOUR passages, so the difference shows up
   honestly as citation problems (for example "not_in_context"), not as a crash.
Change the prompt, the question or the model name, and there is no recording for that request.
"""

import contextlib
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"
KEY_FIELDS = ("model", "messages", "response_format", "max_completion_tokens")
PASSAGE_ID = re.compile(r"^\[([0-9a-f]{12})\] ", re.M)


class ProviderError(Exception):
    """The provider could not give an answer."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class RecordingNotFound(ProviderError):
    """The mock has no recorded response for this exact request."""


@dataclass
class Completion:
    text: str | None
    finish_reason: str
    refusal: str | None
    model: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_s: float
    raw: dict = field(repr=False)
    note: str = ""      # set by the mock when it replays an answer recorded with other passages

    @classmethod
    def from_response(cls, data: dict, latency_s: float) -> "Completion":
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        return cls(text=message.get("content"), finish_reason=choice.get("finish_reason") or "",
                   refusal=message.get("refusal"), model=data.get("model", ""),
                   input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0),
                   reasoning_tokens=details.get("reasoning_tokens") or 0, latency_s=latency_s, raw=data)


def request_key(request: dict) -> str:
    """A stable name for a request: the same fields in, the same key out."""
    fields = {name: request.get(name) for name in KEY_FIELDS}
    text = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def without_passages(request: dict) -> dict:
    """The request with the passages cut from the user message (everything after 'Passages:')."""
    messages = [dict(m, content=m["content"].split("\nPassages:\n", 1)[0]) if m.get("role") == "user" else m
                for m in request.get("messages") or []]
    return {**request, "messages": messages}


def replay_key(request: dict) -> str:
    return request_key(without_passages(request))


def passage_ids(request: dict) -> list[str]:
    users = [m["content"] for m in request.get("messages") or [] if m.get("role") == "user"]
    return PASSAGE_ID.findall(users[-1]) if users else []


class MockProvider:
    """Replays recorded responses. A request that was not recorded raises RecordingNotFound."""

    def __init__(self, folder: Path = RECORDINGS):
        self.recordings = {}
        self.by_question: dict[str, list[dict]] = {}
        for path in sorted(folder.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                if "key" in entry:
                    self.recordings[entry["key"]] = entry
                    if "request" in entry:
                        self.by_question.setdefault(replay_key(entry["request"]), []).append(entry)

    def _find(self, request: dict) -> tuple[dict, str]:
        key = request_key(request)
        if key in self.recordings:
            return self.recordings[key], ""
        candidates = self.by_question.get(replay_key(request))
        if not candidates:
            raise RecordingNotFound(
                f"No recording for this request (key {key}). The mock replays only the questions that were recorded "
                "for the course, with the same prompt and the same model.")
        yours = passage_ids(request)
        entry = max(candidates, key=lambda e: len(set(passage_ids(e["request"])) & set(yours)))   # first one on a tie
        recorded = passage_ids(entry["request"])
        note = (f"Recorded with passages {', '.join(recorded) or 'none'}; yours: {', '.join(yours) or 'none'}. "
                "The recorded answer is replayed; its citations are checked against your passages.")
        return entry, note

    def complete(self, request: dict) -> Completion:
        entry, note = self._find(request)
        if "error" in entry:
            raise ProviderError(f"HTTP {entry['error']['status']}: {entry['error']['message']}", entry["error"]["status"])
        completion = Completion.from_response(entry["response"], entry["latency_s"])
        completion.note = note
        return completion


@contextlib.contextmanager
def translate_errors():
    """Turn the SDK's exceptions into the assistant's own, so that no other file imports `openai`."""
    import openai

    try:
        yield
    except openai.APITimeoutError as e:
        raise ProviderError("The provider did not answer within the timeout.") from e
    except openai.APIStatusError as e:
        raise ProviderError(f"HTTP {e.status_code}: {e.message}", status=e.status_code) from e
    except openai.APIConnectionError as e:
        raise ProviderError("Cannot reach the provider (connection error).") from e


class OpenAICompatibleProvider:
    """Calls a server that speaks the OpenAI-compatible Chat Completions API."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0, headers: dict | None = None):
        from openai import OpenAI

        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed", timeout=timeout_s,
                             max_retries=0, default_headers=headers)

    def complete(self, request: dict) -> Completion:
        start = time.monotonic()
        with translate_errors():
            response = self.client.chat.completions.create(**request)
        return Completion.from_response(response.model_dump(), round(time.monotonic() - start, 3))
