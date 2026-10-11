"""The model side of the host. The host talks to every model through one small interface:

    decide(messages, tools) -> Decision   (tool calls to make, or a final answer)

- MockModel: scripted, no network, no account. It chooses tools with simple rules, so every run
  gives the same messages. The course starts with it.
- OpenAICompatibleModel: a real model through any OpenAI-compatible chat completions API (your own
  key, or a local model server). Optional.
Provider-specific code stays in this file; the host and the MCP client do not change.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

TICKET_ID = re.compile(r"\bT-\d{5}\b")


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Decision:
    tool_calls: list[ToolCall] = field(default_factory=list)
    answer: str | None = None
    usage: dict = field(default_factory=dict)
    raw: dict | None = None


def _tool_results(messages: list[dict]) -> list[dict]:
    """The tool results so far, as the host wrapped them: [{"tool", "result" or "error"}]."""
    out = []
    for m in messages:
        if m["role"] == "tool":
            try:
                out.append(json.loads(m["content"]))
            except json.JSONDecodeError:
                out.append({"tool": "?", "error": m["content"]})
    return out


class MockModel:
    """Rules: 1) a ticket ID in the question -> get_ticket; 2) no search yet -> search_knowledge
    with the question (or the ticket's subject); 3) else answer from the results."""

    name = "mock"

    def decide(self, messages: list[dict], tools: list[dict]) -> Decision:
        names = {t["function"]["name"] for t in tools}
        question = next(m["content"] for m in messages if m["role"] == "user")
        results = _tool_results(messages)
        done = {r.get("tool") for r in results}
        n = len(results)
        ticket = TICKET_ID.search(question)
        if ticket and "get_ticket" in names and "get_ticket" not in done:
            return Decision([ToolCall(f"call_{n + 1}", "get_ticket", {"ticket_id": ticket.group(0)})])
        if "search_knowledge" in names and "search_knowledge" not in done:
            query = question
            for r in results:
                data = r.get("result")
                if r.get("tool") == "get_ticket" and isinstance(data, dict) and "subject" in data:
                    query = data["subject"]
            query = re.sub(r"\s+", " ", TICKET_ID.sub("", query)).strip()[:200]
            return Decision([ToolCall(f"call_{n + 1}", "search_knowledge", {"query": query})])
        return Decision(answer=self._answer(results))

    @staticmethod
    def _answer(results: list[dict]) -> str:
        lines = []
        for r in results:
            data = r.get("result")
            if r.get("error"):
                lines.append(f"I could not use {r.get('tool')}: {r['error']}")
            elif r.get("tool") == "get_ticket" and isinstance(data, dict):
                lines.append(f"Ticket {data.get('ticket_id')} ({data.get('status')}): {data.get('subject')}.")
            elif r.get("tool") == "search_knowledge" and isinstance(data, dict):
                hits = data.get("results", [])
                if hits:
                    best = hits[0]
                    lines.append(f'From "{best["title"]}" ({best["uri"]}): {best["snippet"]}')
                else:
                    lines.append("I found no policy about this.")
        return "\n".join(lines) or "I have no information to answer this."


class OpenAICompatibleModel:
    """Chat completions with tools. Settings (environment): MODEL_BASE_URL (ends with /v1 or
    /openai/v1), MODEL_API_KEY (never printed), MODEL_NAME, MODEL_REASONING_EFFORT (optional; some
    models need "none" to use tools), MODEL_TIMEOUT (seconds, 60)."""

    def __init__(self):
        self.base = os.environ["MODEL_BASE_URL"].rstrip("/")
        self.key = os.environ.get("MODEL_API_KEY", "")
        self.name = os.environ.get("MODEL_NAME", "chat-small")
        self.effort = os.environ.get("MODEL_REASONING_EFFORT")
        self.timeout = float(os.environ.get("MODEL_TIMEOUT", "60"))

    def decide(self, messages: list[dict], tools: list[dict]) -> Decision:
        body = {"model": self.name, "messages": messages, "tools": tools, "max_completion_tokens": 800}
        if self.effort:
            body["reasoning_effort"] = self.effort
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "api-key": self.key, "Authorization": f"Bearer {self.key}"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"model error HTTP {e.code}: {e.read()[:300].decode(errors='replace')}") from None
        msg = data["choices"][0]["message"]
        usage = dict(data.get("usage") or {}) | {"ms": round((time.perf_counter() - started) * 1000)}
        calls = [
            ToolCall(c["id"], c["function"]["name"], json.loads(c["function"]["arguments"] or "{}"))
            for c in msg.get("tool_calls") or []
        ]
        return Decision(calls, None if calls else (msg.get("content") or ""), usage, data)


def make_model(name: str):
    if name == "mock":
        return MockModel()
    if name == "openai":
        return OpenAICompatibleModel()
    raise ValueError(f"unknown model {name!r}: use mock or openai")
