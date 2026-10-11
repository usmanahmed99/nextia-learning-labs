"""Logs: enough to diagnose a failure, nothing secret or personal."""

import io
import json

import anyio
from mcp import Client, MCPError

from idp import keys
from support_mcp import logs
from support_mcp.server import build_server


def test_redact_removes_tokens_emails_and_secret_fields():
    tok = keys.access_token("usr-sam", "knowledge:read", "http://127.0.0.1:8000/mcp")
    out = logs.redact(
        {
            "header": f"Bearer {tok}",
            "note": f"token {tok} from grace@larkfield.example",
            "api_key": "sk-123",
            "settings": {"MODEL_API_KEY": "practice-not-a-real-key", "SUPPORT_TENANT": "larkfield"},
            "nested": [{"password": "x"}],
        }
    )
    text = json.dumps(out)
    assert tok not in text and "grace@larkfield.example" not in text and "sk-123" not in text
    assert out["settings"] == {"MODEL_API_KEY": "[redacted]", "SUPPORT_TENANT": "larkfield"}  # by part of the name
    assert out["header"] == "Bearer [redacted]" and out["note"] == "token [token] from [email]"


def test_an_event_names_who_what_where_and_the_outcome():
    stream = io.StringIO()
    from support_mcp.identity import Caller

    rec = logs.Logger(stream).event(
        "tool_call", caller=Caller("usr-sam", "larkfield", "staff"), tool="get_ticket", outcome="ok", ms=0.1
    )
    assert {"ts", "event", "user", "tenant", "role", "client", "tool", "outcome", "ms"} <= set(rec)
    assert json.loads(stream.getvalue()) == rec


def test_tool_calls_are_logged_without_the_ticket_text(capsys):
    async def go():
        async with Client(build_server()) as client:
            await client.call_tool("get_ticket", {"ticket_id": "T-30002"})

    anyio.run(go)
    err = capsys.readouterr().err
    events = [json.loads(line) for line in err.splitlines() if line.startswith("{")]
    assert events[-1]["tool"] == "get_ticket" and events[-1]["outcome"] == "ok"
    assert "charged two times" not in err  # the customer's words stay out of the logs


def test_every_refusal_writes_one_line_with_the_reason(capsys, monkeypatch):
    async def call(user, scopes, tool, args):
        monkeypatch.setenv("SUPPORT_USER", user)
        monkeypatch.setenv("SUPPORT_SCOPES", scopes)
        async with Client(build_server()) as client:
            try:
                await client.call_tool(tool, args)
            except MCPError as e:
                return e.error.code

    read = "knowledge:read tickets:read"
    codes = [
        anyio.run(call, "usr-tomas", read, "get_ticket", {"ticket_id": "T-30002"}),  # no membership
        anyio.run(call, "usr-sam", "knowledge:read", "get_ticket", {"ticket_id": "T-30002"}),  # no scope
        anyio.run(
            call,
            "usr-omar",
            read + " refunds:propose",
            "propose_refund",  # role read_only
            {"ticket_id": "T-30002", "amount": "25.00", "reason": "Charged twice"},
        ),
    ]
    assert codes == [-32003, -32003, -32003]
    events = [json.loads(line) for line in capsys.readouterr().err.splitlines() if line.startswith("{")]
    refused = [e for e in events if e["event"] == "refused"]
    assert [(e["user"], e["tenant"], e["reason"]) for e in refused] == [
        ("usr-tomas", "larkfield", "no_membership"),
        ("usr-sam", "larkfield", "insufficient_scope"),
        ("usr-omar", "larkfield", "role"),
    ]
    assert all(e["tool"] for e in refused) and len(refused) == len(events)  # one line each, nothing else
