"""The real local transport: the server as a child process, MCP on stdout, logs on stderr."""

import json
import sys

import anyio
from mcp import Client, StdioServerParameters

from scripts import trace


def test_the_sdk_client_starts_the_server_and_calls_a_tool(as_user):
    params = StdioServerParameters(command=sys.executable, args=["-m", "support_mcp"])

    async def go():
        async with Client(params) as client:
            names = [t.name for t in (await client.list_tools()).tools]
            r = await client.call_tool("get_ticket", {"ticket_id": "T-30002"})
            return client.protocol_version, names, r.structured_content["ticket_id"]

    version, names, ticket = anyio.run(go)
    assert version == "2026-07-28" and "get_ticket" in names and ticket == "T-30002"


def test_stdout_carries_only_protocol_messages():
    events = trace.run("discovery", trace.SCENARIOS["discovery"])
    answers = [e for e in events if e["dir"] == "<-"]
    assert [a["message"]["id"] for a in answers] == [1, 2, 3, 4, 5]
    assert all(a["message"]["jsonrpc"] == "2.0" for a in answers)


def test_logs_go_to_stderr_as_json():
    events = trace.run("valid-call", trace.SCENARIOS["valid-call"])
    logs = [json.loads(e["text"]) for e in events if e["dir"] == "log" and e["text"].startswith("{")]
    assert logs and logs[0]["event"] == "tool_call" and logs[0]["tool"] == "get_ticket"


def test_a_wrong_protocol_version_is_refused_with_the_supported_list():
    events = trace.run("version-mismatch", trace.SCENARIOS["version-mismatch"])
    error = [e for e in events if e["dir"] == "<-"][0]["message"]["error"]
    assert error["code"] == -32022 and error["data"]["supported"] == ["2026-07-28"]


def test_an_older_client_still_works_with_the_initialize_handshake():
    events = trace.run("legacy-handshake", trace.SCENARIOS["legacy-handshake"])
    answers = [e["message"] for e in events if e["dir"] == "<-"]
    assert answers[0]["result"]["protocolVersion"] == "2025-11-25"
    assert "get_ticket" in [t["name"] for t in answers[1]["result"]["tools"]]
