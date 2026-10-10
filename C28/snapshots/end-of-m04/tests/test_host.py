"""The host: discovery, the model's proposed calls, the host's decisions, failures."""

import anyio
import pytest
from mcp import Client

from host import app
from host.models import Decision, MockModel, ToolCall
from support_mcp.server import build_server


def ask(question, model=None, confirm=lambda n, a: False):
    async def go():
        async with Client(build_server()) as client:
            return await app.ask(client, model or MockModel(), question, confirm)

    return anyio.run(go)


class Scripted:
    """A model that proposes the given calls once, then answers."""

    def __init__(self, *calls):
        self.calls = list(calls)

    def decide(self, messages, tools):
        if self.calls:
            return Decision([self.calls.pop(0)])
        return Decision(answer="done")


def test_one_request_from_discovery_to_answer():
    run = ask("Draft a reply to T-30002")
    who = [(s.who, s.text.split(":")[0]) for s in run.steps]
    assert who[0] == ("host", "discovered 2 tools") or who[0][1].startswith("discovered")
    assert [s.data.get("arguments") for s in run.steps if s.who == "model" and s.text.startswith("wants")] == [
        {"ticket_id": "T-30002"},
        {"query": "Charged twice for order LK-182074"},
    ]
    assert "policy://larkfield/refunds-and-payments" in run.answer


def test_the_model_sees_tools_in_the_providers_format():
    async def go():
        async with Client(build_server()) as client:
            return [app.tool_spec(t) for t in (await client.list_tools()).tools]

    specs = anyio.run(go)
    assert specs[0]["type"] == "function" and "parameters" in specs[0]["function"]


def test_an_unknown_tool_is_not_sent_to_the_server():
    run = ask("x", Scripted(ToolCall("c1", "delete_everything", {})))
    assert any(s.data.get("decision") == "unknown_tool" for s in run.steps)
    assert not any(s.who == "server" for s in run.steps)


def test_a_slow_tool_times_out(monkeypatch):
    monkeypatch.setenv("SUPPORT_SLOW_SECONDS", "3")  # the server process waits 3 s in every search
    monkeypatch.setattr(app, "TOOL_TIMEOUT_SECONDS", 0.5)

    async def go():
        async with Client(app.server_params("usr-sam", "larkfield")) as client:
            return await app.ask(
                client, Scripted(ToolCall("c1", "search_knowledge", {"query": "returns"})), "x", lambda n, a: False
            )

    run = anyio.run(go)
    assert any(s.data.get("decision") == "timeout" for s in run.steps)


def test_an_oversized_result_is_cut_and_labelled(monkeypatch):
    monkeypatch.setattr(app, "MAX_RESULT_CHARS", 200)
    run = ask("x", Scripted(ToolCall("c1", "search_knowledge", {"query": "returns refund", "limit": 5})))
    assert any(s.data.get("clipped") for s in run.steps if s.who == "server")
    wrapped = app.wrap("search_knowledge", "x" * 500, False)
    assert "result cut to 200 characters" in wrapped


def test_tool_results_reach_the_model_with_the_tools_name():
    assert app.wrap("get_ticket", '{"a": 1}', False) == '{"tool": "get_ticket", "result": {"a": 1}}'
    assert '"error"' in app.wrap("get_ticket", "not_found", True)


def test_a_tool_off_the_allow_list_needs_the_persons_yes(monkeypatch):
    monkeypatch.setattr(app, "AUTO_RUN", set())  # an empty allow-list: every call needs a yes
    asked = []
    run = ask(
        "x",
        Scripted(ToolCall("c1", "search_knowledge", {"query": "returns"})),
        confirm=lambda n, a: asked.append((n, a)) or False,
    )
    assert asked == [("search_knowledge", {"query": "returns"})]
    assert any(s.data.get("decision") == "declined" for s in run.steps)
    assert not any(s.who == "server" for s in run.steps)


@pytest.mark.parametrize("legacy", [False, True])
def test_the_host_works_with_both_protocol_eras(legacy):
    async def go():
        async with Client(app.server_params("usr-sam", "larkfield"), mode="legacy" if legacy else "auto") as c:
            run = await app.ask(c, MockModel(), "What is the return window?", lambda n, a: False)
            return c.protocol_version, run.answer

    version, answer = anyio.run(go)
    assert version == ("2025-11-25" if legacy else "2026-07-28")
    assert "policy://larkfield/" in answer
