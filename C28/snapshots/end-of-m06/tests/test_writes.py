"""The one write: a refund proposal. Authorized on the server, approved by a person, never by the model."""

import anyio
import pytest
from mcp import Client, MCPError

from support_mcp import writes
from support_mcp.approvals import main as approvals
from support_mcp.server import build_server

WRITE_SCOPES = "knowledge:read tickets:read refunds:propose"


def propose(args):
    async def go():
        async with Client(build_server()) as client:
            try:
                r = await client.call_tool("propose_refund", args)
                return ("error" if r.is_error else "ok"), (r.structured_content or r.content[0].text)
            except MCPError as e:
                return "refused", e.error.message

    return anyio.run(go)


REFUND = {"ticket_id": "T-30002", "amount": 25, "reason": "Charged twice for one order"}


def test_the_tool_says_it_is_not_read_only():
    async def go():
        async with Client(build_server()) as client:
            return {t.name: t for t in (await client.list_tools()).tools}["propose_refund"]

    tool = anyio.run(go)
    assert tool.annotations.read_only_hint is False  # a hint for the user interface, not a control


def test_a_proposal_does_nothing_until_an_owner_approves(as_user, capsys):
    as_user("usr-sam", "larkfield", WRITE_SCOPES)
    status, p = propose(REFUND)
    assert status == "ok" and p["status"] == "pending_approval" and p["operation_id"] == "OP-0001"
    assert p["operation"] == {
        "action": "refund",
        "organization": "larkfield",
        "ticket_id": "T-30002",
        "amount": "25.00",
        "currency": "USD",
        "reason": "Charged twice for one order",
    }
    assert writes.refunds() == []
    assert approvals(["approve", "OP-0001", "--user", "usr-grace"]) == 0
    assert "recorded (mock: no money moved)" in capsys.readouterr().out
    assert [r["operation_id"] for r in writes.refunds()] == ["OP-0001"]


def test_the_same_proposal_twice_is_one_proposal(as_user):
    as_user("usr-sam", "larkfield", WRITE_SCOPES)
    assert propose(REFUND)[1]["operation_id"] == propose(REFUND)[1]["operation_id"] == "OP-0001"
    assert len(writes.pending()) == 1


@pytest.mark.parametrize(
    "user,tenant,scopes,expected",
    [
        ("usr-sam", "larkfield", "knowledge:read tickets:read", "insufficient_scope"),  # no write scope
        ("usr-omar", "larkfield", WRITE_SCOPES, "the role read_only cannot propose a refund"),
        ("usr-camille", "bramble", WRITE_SCOPES, "the role read_only cannot propose a refund"),
        ("usr-ines", "larkfield", WRITE_SCOPES, "no access to this organization"),
    ],
)
def test_who_may_not_propose(as_user, user, tenant, scopes, expected):
    as_user(user, tenant, scopes)
    status, message = propose(REFUND)
    assert status == "refused" and expected in message
    assert writes.pending() == []


def test_limits_and_tenant_on_the_write(as_user):
    as_user("usr-sam", "larkfield", WRITE_SCOPES)
    assert "over_limit" in propose(REFUND | {"amount": 450})[1]
    assert "not_found" in propose(REFUND | {"ticket_id": "T-40003"})[1]  # Bramble's ticket
    assert propose(REFUND | {"amount": -5})[0] == "error"
    assert writes.pending() == []


@pytest.mark.parametrize(
    "approver,reason",
    [
        ("usr-sam", "only an owner of larkfield can decide (you: staff)"),
        ("usr-ines", "only an owner of larkfield can decide (you: no membership)"),
    ],
)
def test_only_another_owner_approves(as_user, capsys, approver, reason):
    as_user("usr-sam", "larkfield", WRITE_SCOPES)
    propose(REFUND)
    assert approvals(["approve", "OP-0001", "--user", approver]) == 1
    assert reason in capsys.readouterr().err
    assert writes.refunds() == []


def test_an_owner_cannot_approve_their_own_proposal(as_user, capsys):
    as_user("usr-grace", "larkfield", WRITE_SCOPES)
    propose(REFUND)
    assert approvals(["approve", "OP-0001", "--user", "usr-grace"]) == 1
    assert "another person must approve it" in capsys.readouterr().err


def test_a_decision_is_made_once(as_user, capsys):
    as_user("usr-sam", "larkfield", WRITE_SCOPES)
    propose(REFUND)
    assert approvals(["reject", "OP-0001", "--user", "usr-grace"]) == 0
    assert approvals(["approve", "OP-0001", "--user", "usr-grace"]) == 1
    assert "already rejected" in capsys.readouterr().err
    assert writes.refunds() == []
