"""Who may do what: the access matrix of the help desk, as code.

Three questions decide every request (Module 1 of the authentication course):

1. Who is the caller?            authentication: a user ID ("sub") from a checked token
2. In which organization?        the tenant in the request path, and the caller's membership there
3. What may they do there?       the role of that membership, and the scopes of the token

A role belongs to a membership, not to a person: Camille is staff at Larkfield and
read-only at Bramble Books, so the same person gets two different answers.

`decide()` is a pure function: no database, no web request. That makes the matrix easy to
read, to test and to print (python -m scripts.access_matrix).
"""

from dataclasses import dataclass

ROLES = ("owner", "staff", "read_only")

# What each role may do in its organization.
ROLE_ACTIONS: dict[str, frozenset[str]] = {
    "owner": frozenset(
        {
            "ticket.read",
            "ticket.write",
            "file.read",
            "file.upload",
            "document.read",
            "document.read_staff",
            "member.read",
            "member.manage",
            "export.create",
            "audit.read",
        }
    ),
    "staff": frozenset(
        {
            "ticket.read",
            "ticket.write",
            "file.read",
            "file.upload",
            "document.read",
            "document.read_staff",
            "member.read",
            "export.create",
        }
    ),
    "read_only": frozenset({"ticket.read", "file.read", "document.read"}),
}

ACTIONS = (
    "ticket.read",
    "ticket.write",
    "file.read",
    "file.upload",
    "document.read",
    "document.read_staff",
    "member.read",
    "member.manage",
    "export.create",
    "audit.read",
)

# The token scope that an action needs (from Module 2): what the person allowed the
# application to do for them. A role says what the PERSON may do; a scope says what the
# APPLICATION may do on their behalf. Both must allow the action.
ACTION_SCOPE = {
    "ticket.read": "tickets:read",
    "file.read": "tickets:read",
    "document.read": "tickets:read",
    "document.read_staff": "tickets:read",
    "member.read": "tickets:read",
    "ticket.write": "tickets:write",
    "file.upload": "tickets:write",
    "export.create": "tickets:write",
    "member.manage": "members:manage",
    "audit.read": "members:manage",
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    status: int  # the HTTP status the API answers: 200 (allowed), 403 or 404
    code: str  # allowed | not_a_member | role_cannot | missing_scope
    rule: str  # the rule that made the decision, in words


def decide(role: str | None, action: str, scopes: frozenset[str] | None = None) -> Decision:
    """Decide one action for a caller whose membership in the organization has `role`
    (None: no membership). `scopes`: the token's scopes (None: not checked).

    Without a membership the answer is 404, never 403: an outsider learns nothing, not
    even whether the organization or the record exists. A member who may see the record
    but not change it gets 403: they already know it exists."""
    if action not in ACTION_SCOPE:
        raise ValueError(f"unknown action {action!r}")
    if role is None:
        return Decision(False, 404, "not_a_member", "no membership in this organization")
    if action not in ROLE_ACTIONS.get(role, frozenset()):
        return Decision(False, 403, "role_cannot", f"{role} may not {action}")
    needed = ACTION_SCOPE[action]
    if scopes is not None and needed not in scopes:
        return Decision(False, 403, "missing_scope", f"the token has no {needed} scope")
    return Decision(True, 200, "allowed", f"{role} may {action}")
