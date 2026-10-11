"""Contract and compatibility: the server still offers what clients were promised."""

import json

import anyio
import pytest
from mcp import Client, MCPError

from scripts import contract
from support_mcp.server import build_server


def test_the_server_matches_the_recorded_contract():
    now = json.loads(json.dumps(anyio.run(contract.current), sort_keys=True))
    assert now == json.loads(contract.OUT.read_text(encoding="utf-8")), "run: python -m scripts.contract"


def test_error_shapes_are_stable():
    async def go():
        async with Client(build_server()) as c:
            out = {
                "validation": (await c.call_tool("get_ticket", {"ticket_id": "x"})).is_error,
                "unknown_tool": (await c.call_tool("nope", {})).is_error,
            }
            with pytest.raises(MCPError) as e:
                await c.read_resource("policy://larkfield/no-such-policy")
            out["resource_not_found"] = e.value.error.code
            return out

    assert anyio.run(go) == {"validation": True, "unknown_tool": True, "resource_not_found": -32602}


def test_every_tool_has_a_description_a_bounded_schema_and_annotations():
    data = json.loads(contract.OUT.read_text(encoding="utf-8"))
    for tool in data["tools"]:
        assert tool["description"] and tool["annotations"] and tool["outputSchema"]
        for prop in tool["inputSchema"]["properties"].values():
            assert any(k in json.dumps(prop) for k in ("maxLength", "maximum", "pattern")), (tool["name"], prop)
