"""Module 4 of the authentication course: the server checks every route, every time.

Who (a checked token) -> where (a membership in the organization of the path) -> what (the
role and the scopes). A tenant ID from the browser is never used."""

import pytest

L = "/v1/tenants/larkfield"
B = "/v1/tenants/bramble"


def without_request_id(response) -> dict:
    body = response.json()
    body["error"].pop("request_id", None)
    return body


def test_no_identity_is_401_on_every_ticket_route(api):
    for path in (
        f"{L}/tickets",
        f"{L}/tickets/T-30002",
        f"{L}/tickets/T-30002/similar",
        f"{L}/documents?q=refund",
    ):
        assert api.get(path).status_code == 401, path


def test_an_outsider_gets_the_same_404_as_for_an_organization_that_does_not_exist(client_as):
    tomas = client_as("usr-tomas")
    real = tomas.get(f"{L}/tickets/T-30002")
    made_up = tomas.get("/v1/tenants/acme/tickets/T-30002")
    assert real.status_code == made_up.status_code == 404
    assert without_request_id(real) == without_request_id(made_up)


def test_another_organizations_ticket_looks_like_a_ticket_that_does_not_exist(client_as):
    """Sam guesses a real ID of Bramble Books through his own organization."""
    sam = client_as("usr-sam")
    guessed = sam.get(f"{L}/tickets/T-40001")
    missing = sam.get(f"{L}/tickets/T-49999")
    assert guessed.status_code == missing.status_code == 404
    assert guessed.json()["error"]["message"] == "Ticket T-40001 does not exist."
    assert missing.json()["error"]["message"] == "Ticket T-49999 does not exist."


def test_a_read_only_member_can_read_but_not_write(client_as):
    omar = client_as("usr-omar")
    assert omar.get(f"{L}/tickets/T-30002").status_code == 200
    response = omar.post(f"{L}/tickets/T-30002/messages", json={"author": "agent", "body": "x"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_camille_writes_at_larkfield_and_only_reads_at_bramble(client_as):
    camille = client_as("usr-camille")
    message = {"author": "agent", "body": "Checked."}
    assert camille.post(f"{L}/tickets/T-30002/messages", json=message).status_code == 201
    assert camille.get(f"{B}/tickets/T-40001").status_code == 200
    assert camille.post(f"{B}/tickets/T-40001/messages", json=message).status_code == 403


def test_a_token_without_the_write_scope_cannot_write_even_for_an_owner(make_api, as_user):
    api = make_api()
    response = api.post(
        f"{L}/tickets/T-30002/messages",
        json={"author": "agent", "body": "x"},
        headers=as_user("usr-grace", scope="tickets:read"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_scope"
    assert 'error="insufficient_scope"' in response.headers["www-authenticate"]


@pytest.mark.parametrize("header", ["X-Tenant-ID", "X-Organization"])
def test_a_tenant_header_from_the_browser_changes_nothing(client_as, header):
    page = client_as("usr-sam").get(f"{L}/tickets?limit=100", headers={header: "bramble"})
    assert {t["ticket_id"][:4] for t in page.json()["items"]} == {"T-30"}


def test_a_service_token_is_not_a_member_of_any_organization(make_api, token_for):
    api = make_api()
    token = token_for("export-worker", scope="tickets:read", client_id="export-worker")
    response = api.get(f"{L}/tickets", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_the_browser_session_goes_through_the_same_checks(make_api, provider):
    from tests.test_sessions import sign_in

    browser = make_api()
    sign_in(browser, provider, "usr-omar")
    assert browser.get(f"{L}/tickets/T-30002").status_code == 200
    assert browser.get(f"{B}/tickets/T-40001").status_code == 404
    csrf = browser.get("/auth/session").json()["csrf_token"]
    write = browser.post(
        f"{L}/tickets/T-30002/messages",
        json={"author": "agent", "body": "x"},
        headers={"X-CSRF-Token": csrf},
    )
    assert write.status_code == 403
