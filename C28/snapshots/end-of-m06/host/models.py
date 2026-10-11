"""The model side of the host. The host talks to every model through one small interface:

    decide(messages, tools) -> Decision   (tool calls to make, or a final answer)

- MockModel: scripted, no network, no account. It chooses tools with simple rules, so every run
  gives the same messages. The course starts with it.
- ObedientMockModel: a mock that does what text in a tool result tells it to do (constructed, to
  show that the server's checks stop an injected request whatever the model does).
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
REFUND = re.compile(r"refund of (\d+(?:\.\d{1,2})?)")


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
    """The tool results so far: [{"name", "data"}] (data parsed from the host's JSON wrapper)."""
    out = []
    for m in messages:
        if m["role"] == "tool":
            try:
                out.append(json.loads(m["content"]))
            except json.JSONDecodeError:
                out.append({"tool": "?", "error": m["content"]})
    return out


class MockModel:
    """Rules: 1) a ticket ID in the question -> get_ticket; 2) "refund of N" in the question ->
    propose_refund; 3) no search yet -> search_knowledge with the question (or the ticket's
    subject); 4) else answer from the results."""

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
        refund = REFUND.search(question)
        if ticket and refund and "propose_refund" in names and "propose_refund" not in done:
            return Decision(
                [
                    ToolCall(
                        f"call_{n + 1}",
                        "propose_refund",
                        {
                            "ticket_id": ticket.group(0),
                            "amount": refund.group(1),
                            "reason": "Requested in the help desk",
                        },
                    )
                ]
            )
        if "search_knowledge" in names and "search_knowledge" not in done:
            query = question
            for r in results:
                data = r.get("untrusted_data")
                if r.get("tool") == "get_ticket" and isinstance(data, dict) and "subject" in data:
                    query = data["subject"]
            query = re.sub(r"\s+", " ", TICKET_ID.sub("", query)).strip()[:200]
            return Decision([ToolCall(f"call_{n + 1}", "search_knowledge", {"query": query})])
        return Decision(answer=self._answer(results))

    @staticmethod
    def _answer(results: list[dict]) -> str:
        lines = []
        for r in results:
            data = r.get("untrusted_data")
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
            elif r.get("tool") == "propose_refund" and isinstance(data, dict):
                lines.append(f"Refund proposal {data.get('operation_id')}: {data.get('status')}.")
        return "\n".join(lines) or "I have no information to answer this."


class ObedientMockModel(MockModel):
    """A constructed bad model: after it reads a ticket, it makes every tool call that the ticket's
    text asks for (`call <tool> ... T-12345 ... amount 450`). Labelled constructed every time."""

    name = "mock-obedient (constructed)"

    def decide(self, messages, tools):
        results = _tool_results(messages)
        done = [r.get("tool") for r in results]
        for r in results:
            data = r.get("untrusted_data")
            if r.get("tool") == "get_ticket" and isinstance(data, dict) and "obeyed" not in done:
                text = data.get("body", "")
                calls = []
                if "propose_refund" in text:
                    amount = re.search(r"amount (\d+(?:\.\d+)?)", text)
                    calls.append(
                        ToolCall(
                            "call_inj_1",
                            "propose_refund",
                            {
                                "ticket_id": data["ticket_id"],
                                "amount": amount.group(1) if amount else "450",
                                "reason": "customer is always right",
                            },
                        )
                    )
                for other in TICKET_ID.findall(text):
                    if other != data["ticket_id"]:
                        calls.append(ToolCall(f"call_inj_{len(calls) + 1}", "get_ticket", {"ticket_id": other}))
                if calls and not any(r.get("tool") in ("propose_refund",) for r in results):
                    return Decision(calls)
        return super().decide(messages, tools)


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
    if name == "mock-obedient":
        return ObedientMockModel()
    if name == "openai":
        return OpenAICompatibleModel()
    raise ValueError(f"unknown model {name!r}: use mock, mock-obedient or openai")
