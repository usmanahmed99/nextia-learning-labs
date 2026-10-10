"""Module 6 of the authentication course: the access-control test matrix.

Every person x every organization x every protected route, with the answer the access
matrix (ticket_api/access.py and docs/access-matrix.md) says they must get. Then every
route with each kind of bad identity. A row that fails is an access-control bug.

    python -m pytest tests/test_access_matrix.py
    python -m scripts.matrix_report        runs it and writes docs/test-report.md
"""

import pytest

from ticket_api.access import decide
from ticket_api.files import LocalFileStore

PEOPLE = ["usr-grace", "usr-sam", "usr-omar", "usr-ines", "usr-camille", "usr-tomas", "usr-kwame"]
MEMBERSHIPS = {
    ("larkfield", "usr-grace"): "owner",
    ("larkfield", "usr-sam"): "staff",
    ("larkfield", "usr-omar"): "read_only",
    ("larkfield", "usr-camille"): "staff",
    ("bramble", "usr-ines"): "owner",
    ("bramble", "usr-camille"): "read_only",
}
TICKET = {"larkfield": "T-30002", "bramble": "T-40001"}

# name: (action, method, path, body, status when allowed)
ROUTES = {
    "list tickets": ("ticket.read", "GET", "/tickets", None, 200),
    "read a ticket": ("ticket.read", "GET", "/tickets/{ticket}", None, 200),
    "similar tickets": ("ticket.read", "GET", "/tickets/{ticket}/similar", None, 200),
    "add a message": (
        "ticket.write",
        "POST",
        "/tickets/{ticket}/messages",
        {"author": "agent", "body": "Matrix test."},
        201,
    ),
    "download a file": ("file.read", "GET", "/attachments/{attachment}/download", None, 200),
    "upload a file": (
        "file.upload",
        "POST",
        "/tickets/{ticket}/attachments",
        {"file_name": "m.png", "content_type": "image/png", "size_bytes": 10},
        201,
    ),
    "search documents": ("document.read", "GET", "/documents?q=return", None, 200),
    "list members": ("member.read", "GET", "/members", None, 200),
    "invite a person": (
        "member.manage",
        "POST",
        "/invitations",
        {"email": "new.person@example.com", "role": "read_only"},
        201,
    ),
    "start an export": ("export.create", "POST", "/exports", {}, 202),
    "read the audit": ("audit.read", "GET", "/audit", None, 200),
}


def expected(user: str, tenant: str, route: str) -> int:
    action, *_, ok = ROUTES[route]
    decision = decide(MEMBERSHIPS.get((tenant, user)), action)
    return ok if decision.allowed else decision.status


def call(client, conn, tenant: str, route: str, headers=None):
    _, method, path, body, _ = ROUTES[route]
    attachment = conn.execute(
        "SELECT attachment_id FROM attachments WHERE tenant_id = %s AND status = 'stored'"
        " ORDER BY object_key LIMIT 1",
        (tenant,),
    ).fetchone()["attachment_id"]
    url = f"/v1/tenants/{tenant}" + path.format(ticket=TICKET[tenant], attachment=attachment)
    return client.request(method, url, json=body, headers=headers or {})


CASES = [(u, t, r) for u in PEOPLE for t in ("larkfield", "bramble") for r in ROUTES]


@pytest.mark.parametrize("user, tenant, route", CASES, ids=[f"{u}|{t}|{r}" for u, t, r in CASES])
def test_matrix(make_api, conn, tmp_path, user, tenant, route):
    client = make_api(user=user)
    client.app.state.files = LocalFileStore(tmp_path / "files")
    response = call(client, conn, tenant, route)
    assert response.status_code == expected(user, tenant, route), response.text


# A member of one organization uses the right path, but the ID of the other organization's
# record (BOLA: a guessed or copied ID). The answer must be "not found".
BOLA = [
    ("usr-sam", "larkfield", "T-40001"),
    ("usr-ines", "bramble", "T-30002"),
    ("usr-camille", "larkfield", "T-40001"),
    ("usr-camille", "bramble", "T-30002"),
]


@pytest.mark.parametrize(
    "user, tenant, other_ticket", BOLA, ids=[f"{u}|{t}|{o}" for u, t, o in BOLA]
)
def test_another_organizations_record_id(make_api, user, tenant, other_ticket):
    client = make_api(user=user)
    base = f"/v1/tenants/{tenant}/tickets/{other_ticket}"
    assert client.get(base).status_code == 404
    assert client.get(f"{base}/similar").status_code == 404
    message = {"author": "agent", "body": "x"}
    status = client.post(f"{base}/messages", json=message).status_code
    assert status == (403 if MEMBERSHIPS[(tenant, user)] == "read_only" else 404)


# Bad identities on every route: none, expired, for another audience, an ID token, a
# token without the needed scope.
def bad_headers(kind: str, token_for, signer, idp_store) -> dict:
    if kind == "no identity":
        return {}
    if kind == "expired":
        return {"Authorization": f"Bearer {token_for('usr-grace', exp=1, iat=0, nbf=0)}"}
    if kind == "wrong audience":
        return {"Authorization": f"Bearer {token_for('usr-grace', aud='billing-api')}"}
    if kind == "ID token":
        user = idp_store.users()["usr-grace"]
        return {"Authorization": f"Bearer {signer.id_token(user, 'help-desk-web', 'n', 0)}"}
    if kind == "no scope":
        return {"Authorization": f"Bearer {token_for('usr-grace', scope='')}"}
    raise ValueError(kind)


BAD = ["no identity", "expired", "wrong audience", "ID token", "no scope"]
BAD_CASES = [(k, r) for k in BAD for r in ROUTES]


@pytest.mark.parametrize("kind, route", BAD_CASES, ids=[f"{k}|{r}" for k, r in BAD_CASES])
def test_bad_identity(make_api, conn, token_for, signer, idp_store, kind, route):
    client = make_api()
    response = call(
        client, conn, "larkfield", route, headers=bad_headers(kind, token_for, signer, idp_store)
    )
    want = 403 if kind == "no scope" else 401
    assert response.status_code == want, response.text
