"""Module 6, lesson 2: the audit answers who did what, and who tried, without a single token,
cookie, secret or invitation code in it."""

import json
import re

from tests.test_sessions import csrf, sign_in

JWT = re.compile(r"eyJ[\w-]+\.[\w-]+\.[\w-]*")
L = "/v1/tenants/larkfield"


def events(conn, **where):
    sql = "SELECT * FROM audit_events"
    if where:
        sql += " WHERE " + " AND ".join(f"{k} = %({k})s" for k in where)
    return conn.execute(sql + " ORDER BY event_id", where).fetchall()


def test_a_denied_attempt_is_recorded_with_who_what_and_why(client_as, conn):
    client_as("usr-omar").post(
        f"{L}/tickets/T-30002/messages", json={"author": "agent", "body": "x"}
    )
    [e] = events(conn, actor_id="usr-omar")
    assert (e["action"], e["result"], e["reason"], e["tenant_id"]) == (
        "ticket.write",
        "denied",
        "role_cannot",
        "larkfield",
    )


def test_an_outsiders_attempt_is_not_written_into_the_organizations_log(client_as, conn):
    client_as("usr-sam").get("/v1/tenants/bramble/tickets/T-40001")
    [e] = events(conn, actor_id="usr-sam")
    assert e["tenant_id"] is None and e["details"]["tenant_in_path"] == "bramble"
    assert e["reason"] == "not_a_member"


def test_a_refused_token_is_recorded_without_the_token(make_api, token_for, conn):
    expired = token_for("usr-grace", exp=1, iat=0, nbf=0)
    make_api().get(f"{L}/tickets", headers={"Authorization": f"Bearer {expired}"})
    [e] = events(conn, action="token.check")
    assert e["reason"] == "expired" and e["actor_id"] is None


def test_no_token_cookie_secret_or_code_reaches_the_audit_or_the_log(
    make_api, provider, client_as, conn, caplog, idp_store, token_for
):
    caplog.set_level("INFO")
    browser = make_api()
    sign_in(browser, provider, "usr-grace")
    cookie = browser.cookies["ticket_session"]
    grace = client_as("usr-grace")
    invite = grace.post(
        f"{L}/invitations", json={"email": "x@larkfield.example", "role": "staff"}
    ).json()
    browser.post("/auth/logout", headers=csrf(browser))
    grace.get("/v1/tenants/bramble/tickets", headers={"Authorization": "Bearer abc.def.ghi"})
    secrets = [
        cookie,
        invite["code"],
        idp_store.secrets["help-desk-web"],
        token_for("usr-grace")[:40],
    ]
    stored = json.dumps(events(conn), default=str)
    logged = caplog.text
    for text in (stored, logged):
        assert not JWT.search(text)
        assert not any(s in text for s in secrets)
    actions = {e["action"] for e in events(conn)}
    assert {"sign_in", "invitation.created", "sign_out", "token.check"} <= actions


def test_the_audit_is_append_only(conn, client_as):
    import psycopg
    import pytest

    client_as("usr-omar").get("/v1/tenants/bramble/tickets")
    with pytest.raises(psycopg.errors.RaiseException, match="cannot be changed"):
        conn.execute("DELETE FROM audit_events")
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("UPDATE audit_events SET result = 'allowed'")
