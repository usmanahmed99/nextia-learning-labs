"""Module 1: the access matrix in code (ticket_api/access.py), without a database."""

import pytest

from ticket_api.access import ACTIONS, ROLE_ACTIONS, decide

# The matrix of the course, row by row: owner, staff, read_only (True = allowed).
MATRIX = {
    "ticket.read": (True, True, True),
    "ticket.write": (True, True, False),
    "file.read": (True, True, True),
    "file.upload": (True, True, False),
    "document.read": (True, True, True),
    "document.read_staff": (True, True, False),
    "member.read": (True, True, False),
    "member.manage": (True, False, False),
    "export.create": (True, True, False),
    "audit.read": (True, False, False),
}


@pytest.mark.parametrize("action", ACTIONS)
@pytest.mark.parametrize("i, role", list(enumerate(["owner", "staff", "read_only"])))
def test_the_code_is_the_matrix(action, i, role):
    assert decide(role, action).allowed is MATRIX[action][i]


def test_no_membership_is_404_for_every_action():
    assert {decide(None, a).status for a in ACTIONS} == {404}


def test_a_role_that_cannot_is_403_and_names_the_rule():
    d = decide("read_only", "ticket.write")
    assert (d.status, d.code, d.rule) == (403, "role_cannot", "read_only may not ticket.write")


def test_camille_gets_two_answers_for_one_action():
    """Staff at Larkfield, read-only at Bramble Books: the role comes from the membership."""
    memberships = {"larkfield": "staff", "bramble": "read_only"}
    assert decide(memberships["larkfield"], "ticket.write").allowed
    assert not decide(memberships["bramble"], "ticket.write").allowed
    assert decide(memberships.get("acme"), "ticket.read").status == 404


def test_a_scope_must_allow_the_action_too():
    assert decide("owner", "ticket.write", frozenset({"tickets:read"})).code == "missing_scope"
    assert decide("owner", "ticket.write", frozenset({"tickets:write"})).allowed


def test_no_role_has_an_unknown_action():
    for actions in ROLE_ACTIONS.values():
        assert actions <= set(ACTIONS)
    with pytest.raises(ValueError):
        decide("owner", "ticket.delete")
