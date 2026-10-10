"""Module 4, lesson 3: pages of a fixed size, keyset pagination, one query per page."""

import pytest


@pytest.fixture
def api(grace):
    """Since the authentication course, the ticket routes need a member: Grace, at Larkfield."""
    return grace


def walk(api, **params):
    seen, after, pages = [], None, 0
    while True:
        response = api.get(
            "/v1/tenants/larkfield/tickets",
            params={**params, **({"after": after} if after else {})},
        )
        assert response.status_code == 200
        # no N+1: one query for the whole page. The authentication course adds two: the
        # membership check, and the organization of the transaction (row-level security)
        assert response.headers["X-DB-Queries"] == "3"
        page = response.json()
        seen += [t["ticket_id"] for t in page["items"]]
        pages += 1
        after = page["next"]
        if after is None:
            return seen, pages


def test_the_pages_together_have_every_ticket_once(api, conn):
    seen, pages = walk(api, limit=30)
    assert len(seen) == len(set(seen)) == 200  # Larkfield's tickets only: never Bramble's
    assert pages == 7


def test_a_filtered_walk_has_every_matching_ticket(api, conn):
    seen, _ = walk(api, status="closed", limit=7)
    expected = conn.execute(
        "SELECT count(*) AS n FROM tickets WHERE tenant_id = 'larkfield' AND status = 'closed'"
    ).fetchone()["n"]
    assert len(seen) == len(set(seen)) == expected


def test_a_new_ticket_does_not_shift_the_next_page(api, conn):
    first = api.get("/v1/tenants/larkfield/tickets", params={"limit": 10}).json()
    conn.execute(
        "INSERT INTO tickets (tenant_id, ticket_id, customer_id, subject, body, channel, team,"
        " priority) VALUES ('larkfield', 'T-39999', 'C-0001', 'New', 'A new ticket', 'email',"
        " 'other', 2)"
    )
    second = api.get(
        "/v1/tenants/larkfield/tickets", params={"limit": 10, "after": first["next"]}
    ).json()
    ids = {t["ticket_id"] for t in first["items"]} & {t["ticket_id"] for t in second["items"]}
    assert ids == set()  # with OFFSET, the newest ticket would push one row onto page 2 again


def test_a_broken_cursor_is_422(api):
    response = api.get("/v1/tenants/larkfield/tickets", params={"after": "not-a-cursor"})
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == ["after"]


def test_the_page_size_has_a_maximum(api):
    assert api.get("/v1/tenants/larkfield/tickets", params={"limit": 101}).status_code == 422
