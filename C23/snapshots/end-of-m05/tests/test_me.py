"""Module 2: GET /v1/me answers "who is calling?" from the token, and "where?" from the database."""


def test_sam_is_staff_at_larkfield(api, as_user):
    me = api.get("/v1/me", headers=as_user("usr-sam")).json()
    assert me["user_id"] == "usr-sam" and me["name"] == "Sam" and me["kind"] == "user"
    assert me["memberships"] == [
        {"tenant_id": "larkfield", "tenant_name": "Larkfield", "role": "staff"}
    ]


def test_camille_has_two_memberships_with_two_roles(api, as_user):
    me = api.get("/v1/me", headers=as_user("usr-camille")).json()
    assert [(m["tenant_id"], m["role"]) for m in me["memberships"]] == [
        ("bramble", "read_only"),
        ("larkfield", "staff"),
    ]


def test_tomas_signs_in_but_belongs_nowhere(api, as_user):
    me = api.get("/v1/me", headers=as_user("usr-tomas")).json()
    assert me["name"] == "Tomás" and me["memberships"] == []


def test_kwame_is_a_platform_administrator_without_membership(api, as_user):
    me = api.get("/v1/me", headers=as_user("usr-kwame")).json()
    assert me["platform_role"] == "platform_admin" and me["memberships"] == []


def test_a_service_token_is_not_a_person(api, token_for):
    token = token_for("export-worker", scope="tickets:read", client_id="export-worker")
    me = api.get("/v1/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["kind"] == "service" and me["name"] is None and me["memberships"] == []


def test_the_scopes_come_from_the_token(api, as_user):
    me = api.get("/v1/me", headers=as_user("usr-sam", scope="tickets:read")).json()
    assert me["scopes"] == ["tickets:read"]


def test_without_a_provider_sign_in_is_off(make_api, as_user):
    api = make_api(oidc_issuer=None)
    response = api.get("/v1/me", headers=as_user("usr-sam"))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "sign_in_unavailable"
