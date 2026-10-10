"""Writes wait for approval and respect the role, and the output check holds a leaking answer.
These controls arrive when the course constrains the consequences of a mistake."""

from support_assistant.context import check_answer
from support_assistant.data import made_up_secrets
from support_assistant.runner import fresh_world
from tests._helpers import SECURE, WEAK, run, session


def test_write_needs_approval_and_respects_role_limits():
    w = fresh_world()
    t = w.ticket("T-24002")   # customer C-50533, order LK-640436 (delivered, 89 dollars)
    proposed = run("issue_refund", {"order_id": "LK-640436", "amount": 89.0}, SECURE, session(), t, w)
    assert proposed.proposal is not None and not proposed.proposal.executed and not proposed.proposal.refused_reason
    big = run("issue_refund", {"order_id": "LK-640436", "amount": 149.0}, SECURE, session(), t, w)
    assert big.proposal.refused_reason and "limit" in big.proposal.refused_reason
    owner = run("issue_refund", {"order_id": "LK-640436", "amount": 149.0}, SECURE,
                session(role="owner", sub="usr-grace"), t, w)
    assert not owner.proposal.refused_reason


def test_read_only_member_may_not_write():
    w = fresh_world()
    t = w.ticket("T-24011")
    out = run("issue_refund", {"order_id": "LK-702219", "amount": 9.95}, SECURE,
              session(role="read_only", sub="usr-omar"), t, w)
    assert out.proposal.refused_reason


def test_email_only_to_the_address_on_file():
    w = fresh_world()
    t = w.ticket("T-24002")   # C-50533 = priti.shah@mail.example
    good = run("send_email", {"to": "priti.shah@mail.example", "subject": "x", "body": "y"}, SECURE, session(), t, w)
    assert not good.proposal.refused_reason
    bad = run("send_email", {"to": "attacker@evil.example", "subject": "x", "body": "y"}, SECURE, session(), t, w)
    assert bad.proposal.refused_reason


def test_weak_write_runs_at_once():
    w = fresh_world(redact_log=False)
    t = w.ticket("T-24002")
    out = run("issue_refund", {"order_id": "LK-640436", "amount": 500.0}, WEAK, session(), t, w)
    assert out.proposal.executed and out.proposal.execution_id


def test_output_check_catches_secret_and_outside_link():
    assert check_answer("Here is the key " + made_up_secrets()[0])
    assert check_answer("Please open https://collector.attacker.example/p?x=1")
    assert check_answer("![pixel](https://collector.attacker.example/p.png)")
    assert check_answer("Your parcel ships 13 October. See https://help.larkfield.example/returns") == ""
