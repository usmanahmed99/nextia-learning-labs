"""A ticket whose text tells the model to call the write tool and to read the other organization.
The model here is a constructed one that obeys (ObedientMockModel). The person even says yes.
The server's checks stop it anyway."""

import anyio
from mcp import Client

from host import app
from host.models import ObedientMockModel
from support_mcp import writes
from support_mcp.server import build_server


def attack(confirm=lambda n, a: True):
    async def go():
        async with Client(build_server()) as client:
            return await app.ask(client, ObedientMockModel(), "Please check ticket T-30201.", confirm)

    return anyio.run(go)


def server_lines(run):
    return [s.text for s in run.steps if s.who == "server"]


def test_the_injected_write_and_cross_tenant_read_fail_for_staff(as_user):
    as_user("usr-sam", "larkfield", "knowledge:read tickets:read refunds:propose")
    run = attack()
    wanted = [s.text for s in run.steps if s.who == "model" and s.text.startswith("wants")]
    assert wanted[:3] == ["wants get_ticket", "wants propose_refund", "wants get_ticket"]  # it obeyed
    lines = server_lines(run)
    assert any("over_limit" in t for t in lines)  # 450 dollars: over the agent's limit
    assert any("no ticket T-40003 in this organization" in t for t in lines)
    assert writes.pending() == [] and writes.refunds() == []


def test_a_read_only_member_cannot_be_used_for_the_write(as_user):
    as_user("usr-omar", "larkfield", "knowledge:read tickets:read refunds:propose")
    lines = server_lines(attack())
    assert any("the role read_only cannot propose a refund" in t for t in lines)
    assert writes.pending() == []


def test_without_the_write_scope_the_write_is_refused(as_user):
    as_user("usr-sam", "larkfield", "knowledge:read tickets:read")
    lines = server_lines(attack())
    assert any("insufficient_scope" in t for t in lines)


def test_the_person_can_say_no_first(as_user):
    as_user("usr-sam", "larkfield", "knowledge:read tickets:read refunds:propose")
    run = attack(confirm=lambda n, a: False)
    assert any(s.data.get("decision") == "declined" for s in run.steps)
    assert writes.pending() == []
