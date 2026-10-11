"""The server through the SDK's client, in the same process (the same messages as stdio)."""

import anyio
import pytest
from mcp import Client, MCPError

from support_mcp.server import build_server


def run(fn):
    async def go():
        async with Client(build_server()) as client:
            return await fn(client)

    return anyio.run(go)


def text(result):
    return result.content[0].text


def test_discovery_lists_the_read_only_tools_with_schemas():
    async def go(c):
        return {t.name: t for t in (await c.list_tools()).tools}

    tools = run(go)
    assert {"search_knowledge", "get_ticket"} <= set(tools)
    for name in ("search_knowledge", "get_ticket"):
        assert tools[name].annotations.read_only_hint is True
        assert tools[name].output_schema is not None
    assert tools["get_ticket"].input_schema["properties"]["ticket_id"]["pattern"] == r"^T-\d{5}$"
    assert tools["search_knowledge"].input_schema["properties"]["limit"]["maximum"] == 5


def test_search_returns_structured_bounded_results():
    async def go(c):
        return await c.call_tool("search_knowledge", {"query": "return a damaged item", "limit": 2})

    r = run(go)
    assert not r.is_error
    hits = r.structured_content["results"]
    assert [h["doc_id"] for h in hits] == ["damaged-or-wrong-items", "returns-policy"]
    assert hits[0]["uri"] == "policy://larkfield/damaged-or-wrong-items"


def test_a_valid_ticket_call():
    async def go(c):
        return await c.call_tool("get_ticket", {"ticket_id": "T-30002"})

    r = run(go)
    assert not r.is_error
    assert r.structured_content["subject"] == "Charged twice for order LK-182074"
    assert r.structured_content["customer_name"] == "Hugo"  # first name only: no e-mail, no surname


@pytest.mark.parametrize("args", [{"ticket_id": "30002"}, {}, {"ticket_id": 5}])
def test_a_validation_failure_is_a_tool_error(args):
    async def go(c):
        return await c.call_tool("get_ticket", args)

    r = run(go)
    assert r.is_error and "validation error" in text(r)


def test_too_many_results_is_refused():
    async def go(c):
        return await c.call_tool("search_knowledge", {"query": "returns", "limit": 50})

    assert run(go).is_error


def test_an_unknown_tool_is_reported():
    async def go(c):
        return await c.call_tool("delete_ticket", {"ticket_id": "T-30002"})

    r = run(go)
    # SDK 2.3.0 answers with a tool error (isError); the specification asks for a protocol error.
    assert r.is_error and text(r) == "Unknown tool: delete_ticket"


def test_the_other_organizations_ticket_is_not_found():
    async def go(c):
        return await c.call_tool("get_ticket", {"ticket_id": "T-40003"})

    r = run(go)
    assert r.is_error and "not_found" in text(r)


def test_resources_list_only_the_callers_organization():
    async def go(c):
        return [r.uri for r in (await c.list_resources()).resources]

    uris = run(go)
    assert len(uris) == 9 and all(u.startswith("policy://larkfield/") for u in uris)


def test_read_only_members_do_not_see_staff_documents(as_user):
    as_user("usr-omar", "larkfield")

    async def go(c):
        return [r.uri for r in (await c.list_resources()).resources]

    uris = run(go)
    assert "policy://larkfield/refund-approval-procedure" not in uris and len(uris) == 8


def test_read_a_resource_and_not_another_organizations():
    async def go(c):
        ok = await c.read_resource("policy://larkfield/gift-cards")
        with pytest.raises(MCPError) as e:
            await c.read_resource("policy://bramble/returns-policy")
        return ok, e.value.error

    ok, err = run(go)
    assert ok.contents[0].text.startswith("# Gift cards")
    assert err.code == -32602 and err.data == {"uri": "policy://bramble/returns-policy"}


def test_the_prompt_is_listed_and_filled():
    async def go(c):
        prompts = (await c.list_prompts()).prompts
        got = await c.get_prompt("draft_reply", {"ticket_id": "T-30002"})
        return prompts, got

    prompts, got = run(go)
    assert [p.name for p in prompts] == ["draft_reply"]
    assert "T-30002" in got.messages[0].content.text


def test_someone_without_a_membership_gets_nothing(as_user):
    as_user("usr-tomas", "larkfield")

    async def go(c):
        with pytest.raises(MCPError) as e:
            await c.call_tool("search_knowledge", {"query": "returns"})
        return e.value.error

    err = run(go)
    assert err.code == -32003 and "no access to this organization" in err.message


def test_a_missing_scope_is_refused(as_user):
    as_user("usr-sam", "larkfield", scopes="knowledge:read")

    async def go(c):
        with pytest.raises(MCPError) as e:
            await c.call_tool("get_ticket", {"ticket_id": "T-30002"})
        return e.value.error

    assert "insufficient_scope" in run(go).message
