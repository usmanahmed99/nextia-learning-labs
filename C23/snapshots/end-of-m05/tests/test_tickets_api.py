"""Module 3: the ticket endpoints, on the small data."""

import pytest


@pytest.fixture
def api(grace):
    """Since the authentication course, the ticket routes need a member: Grace, at Larkfield."""
    return grace


def test_list_returns_the_newest_tickets_first(api):
    page = api.get("/v1/tenants/larkfield/tickets", params={"limit": 5}).json()
    times = [t["created_at"] for t in page["items"]]
    assert len(times) == 5 and times == sorted(times, reverse=True)
    assert page["items"][0]["customer_name"]


def test_list_filters_by_status_and_team(api):
    items = api.get(
        "/v1/tenants/larkfield/tickets", params={"status": "open", "team": "billing", "limit": 100}
    ).json()["items"]
    assert items and {(t["status"], t["team"]) for t in items} == {("open", "billing")}


def test_a_customer_sees_only_their_tickets(api):
    items = api.get(
        "/v1/tenants/larkfield/tickets", params={"customer_id": "C-0003", "limit": 100}
    ).json()["items"]
    assert items and {t["customer_id"] for t in items} == {"C-0003"}


def test_one_ticket_with_its_messages(api):
    ticket = api.get("/v1/tenants/larkfield/tickets/T-30002").json()
    assert ticket["ticket_id"] == "T-30002"
    assert len(ticket["messages"]) == ticket["message_count"]


def test_a_missing_ticket_is_404(api):
    response = api.get("/v1/tenants/larkfield/tickets/T-99999")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Ticket T-99999 does not exist."


def test_adding_a_message_updates_the_ticket(api):
    before = api.get("/v1/tenants/larkfield/tickets/T-30002").json()
    response = api.post(
        "/v1/tenants/larkfield/tickets/T-30002/messages",
        json={"author": "customer", "body": "Any news?"},
    )
    assert response.status_code == 201
    after = api.get("/v1/tenants/larkfield/tickets/T-30002").json()
    assert after["message_count"] == before["message_count"] + 1
    assert after["status"] == "open"
    assert after["messages"][-1]["body"] == "Any news?"


def test_an_agent_reply_waits_for_the_customer(api):
    api.post(
        "/v1/tenants/larkfield/tickets/T-30002/messages",
        json={"author": "agent", "body": "We sent it today."},
    )
    assert api.get("/v1/tenants/larkfield/tickets/T-30002").json()["status"] == "pending"


def test_a_message_needs_a_known_author(api):
    response = api.post(
        "/v1/tenants/larkfield/tickets/T-30002/messages", json={"author": "robot", "body": "Hi"}
    )
    assert response.status_code == 422


def test_the_list_needs_a_signed_in_member(make_api):
    """Since the authentication course: no identity, no tickets (the API key is not enough)."""
    anonymous = make_api(api_key="secret-key")
    response = anonymous.get("/v1/tenants/larkfield/tickets", headers={"X-API-Key": "secret-key"})
    assert response.status_code == 401
