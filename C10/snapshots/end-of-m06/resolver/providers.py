"""The adapter: the only code that talks to a model provider.

The workflow builds a request (a dict in the Chat Completions format) and gets back a `Completion`.
Two providers do the work:

- MockProvider replays the model decisions that were recorded for the course. No account, no network.
- OpenAICompatibleProvider calls any server that speaks the OpenAI-compatible Chat Completions API:
  a local Ollama server, OpenAI, or another provider. Its settings come from environment variables.

How the mock finds a recording (robust replay). Every call also passes `meta`: the task, the
variant (fixed, router, agent, workers...), the step number and a short digest of the evidence so far.
1. The exact request was recorded: it replays silently.
2. Otherwise the mock looks for a recording of the same model, variant, task and step. It replays it
   and sets `Completion.note`, so that the run can warn: "your request differs from the recorded
   one". The workflow then checks the replayed decision against YOUR state, as it checks any model
   decision: a call that does not fit is refused, never trusted.
3. Nothing recorded for this task and step: RecordingNotFound. The loop stops with a clear reason.
"""

import contextlib
import email.utils
import gzip
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RECORDINGS = Path(__file__).resolve().parent.parent / "recordings"
KEY_FIELDS = ("model", "messages", "response_format", "tools", "tool_choice", "max_completion_tokens")


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
    """The mock has no recorded decision for this task and step."""


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
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_s: float
    raw: dict = field(repr=False)
    note: str = ""          # set by the mock when it replays a recording made from a different request
    recorded_at: str = ""   # set by the mock: when the decision was recorded

    @classmethod
    def from_response(cls, data: dict, latency_s: float) -> "Completion":
        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        calls = [ToolCall(c["id"], c["function"]["name"], c["function"]["arguments"])
                 for c in message.get("tool_calls") or []]
        return cls(text=message.get("content"), finish_reason=choice.get("finish_reason") or "",
                   refusal=message.get("refusal"), tool_calls=calls, model=data.get("model", ""),
                   input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0),
                   reasoning_tokens=details.get("reasoning_tokens") or 0, latency_s=latency_s, raw=data)


def request_key(request: dict) -> str:
    """A stable name for a request: the same fields in, the same key out."""
    fields = {name: request.get(name) for name in KEY_FIELDS}
    text = json.dumps(fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def replay_key(model: str, meta: dict) -> str:
    return f"{model}|{meta.get('variant')}|{meta.get('task_id')}|{meta.get('step')}"


class MockProvider:
    """Replays recorded decisions (see the module docstring). `repeat` chooses among repeated recordings."""

    def __init__(self, folder: Path = RECORDINGS, repeat: int = 1):
        self.repeat = repeat
        self.exact: dict[str, dict[int, dict]] = {}
        self.by_step: dict[str, dict[int, dict]] = {}
        for path in sorted([*folder.glob("*.jsonl"), *folder.glob("*.jsonl.gz")]):
            raw = path.read_bytes()
            text = gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")
            for line in text.splitlines():
                entry = json.loads(line)
                if "key" not in entry:
                    continue
                meta = entry.get("meta") or {}
                rep = meta.get("repeat", 1)
                self.exact.setdefault(entry["key"], {}).setdefault(rep, entry)
                if meta.get("task_id"):
                    self.by_step.setdefault(replay_key(entry["request"]["model"], meta), {}).setdefault(rep, entry)

    def repeats(self, model: str, variant: str, task_id: str) -> list[int]:
        """The repeat numbers recorded for this model, variant and task (step 1)."""
        found = self.by_step.get(replay_key(model, {"variant": variant, "task_id": task_id, "step": 1}), {})
        return sorted(found)

    def _pick(self, entries: dict[int, dict], repeat: int) -> dict:
        return entries.get(repeat) or entries[min(entries)]

    def complete(self, request: dict, meta: dict | None = None) -> Completion:
        meta = meta or {}
        repeat = meta.get("repeat") or self.repeat
        key = request_key(request)
        note = ""
        entries = self.exact.get(key)
        if entries and meta.get("task_id"):
            # The same request can be recorded for several tasks only by accident; prefer this task's.
            same = {r: e for r, e in entries.items() if (e.get("meta") or {}).get("task_id") == meta["task_id"]}
            entries = same or entries
        if not entries:
            entries = self.by_step.get(replay_key(request.get("model", ""), meta))
            if not entries:
                raise RecordingNotFound(
                    f"No recorded decision for {request.get('model')} / {meta.get('variant')} / "
                    f"{meta.get('task_id')} / step {meta.get('step')} (key {key}). The mock replays only the "
                    "tasks, variants and models that were recorded for the course.")
            entry = self._pick(entries, repeat)
            recorded = (entry.get("meta") or {}).get("state", "")
            note = (f"Your request at step {meta.get('step')} differs from the recorded one (evidence {meta.get('state')} "
                    f"here, {recorded} when recorded). The recorded decision is replayed and checked against your state.")
        else:
            entry = self._pick(entries, repeat)
        if "error" in entry:
            message = entry["error"]["message"]
            if not message.startswith("HTTP"):
                message = f"HTTP {entry['error']['status']}: {message}"
            raise ProviderError(message, entry["error"]["status"])
        completion = Completion.from_response(entry["response"], entry["latency_s"])
        completion.note = note
        completion.recorded_at = entry.get("at", "")
        return completion


def retry_after_s(headers) -> float | None:
    """The wait that a 429 response asks for, in seconds, or None (retry-after-ms first, then retry-after)."""
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        value = headers.get(name)
        if value is None:
            continue
        try:
            return max(0.0, float(value) * scale)
        except ValueError:
            pass
        try:
            when = email.utils.parsedate_to_datetime(value)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            pass
    return None


@contextlib.contextmanager
def translate_errors():
    """Turn the SDK's exceptions into the workflow's own, so that no other file imports `openai`."""
    import openai

    try:
        yield
    except openai.APITimeoutError as e:
        raise ProviderTimeout("The provider did not answer within the timeout.") from e
    except openai.RateLimitError as e:
        raise RateLimited("HTTP 429: rate limited.", retry_after_s(e.response.headers)) from e
    except openai.APIStatusError as e:
        raise ProviderError(f"HTTP {e.status_code}: {e.message}", status=e.status_code) from e
    except openai.APIConnectionError as e:
        raise ProviderError("Cannot reach the provider (connection error).") from e


class OpenAICompatibleProvider:
    """Calls a server that speaks the OpenAI-compatible Chat Completions API. `meta` is not sent."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float = 60.0, reasoning_effort: str = ""):
        from openai import OpenAI  # imported here, so that the mock works without the SDK set up

        # max_retries=0: the workflow decides about retries itself.
        self.client = OpenAI(base_url=base_url, api_key=api_key or "not-needed", timeout=timeout_s, max_retries=0)
        self.reasoning_effort = reasoning_effort

    def complete(self, request: dict, meta: dict | None = None) -> Completion:
        body = dict(request)
        if self.reasoning_effort and "reasoning_effort" not in body:
            body["reasoning_effort"] = self.reasoning_effort
        start = time.monotonic()
        with translate_errors():
            response = self.client.chat.completions.create(**body)
        return Completion.from_response(response.model_dump(), round(time.monotonic() - start, 3))
