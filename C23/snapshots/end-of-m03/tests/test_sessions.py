"""Module 3 of the authentication course: browser sessions through the API (a backend for
frontend). The tests play the browser: they follow each redirect by hand."""

from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import pytest

from tests.conftest import ISSUER


def follow(location: str) -> str:
    """The path and query of an absolute URL (the test clients have no host)."""
    u = urlparse(location)
    return u.path + (f"?{u.query}" if u.query else "")


def sign_in(api, provider, user="usr-sam", prompt=None, return_to="/app/"):
    """Click "Sign in", pick a person at the provider, come back. Returns the callback answer."""
    params = {"return_to": return_to, **({"prompt": prompt} if prompt else {})}
    start = api.get("/auth/login", params=params, follow_redirects=False)
    assert start.status_code == 302 and start.headers["location"].startswith(ISSUER)
    chosen = provider.post(
        follow(start.headers["location"]), data={"user": user}, follow_redirects=False
    )
    assert chosen.status_code == 302
    return api.get(follow(chosen.headers["location"]), follow_redirects=False)


def csrf(api) -> dict:
    return {"X-CSRF-Token": api.get("/auth/session").json()["csrf_token"]}


def test_sign_in_sets_an_httponly_cookie_and_the_api_knows_the_person(api, provider):
    back = sign_in(api, provider, "usr-camille")
    assert back.status_code == 302 and back.headers["location"] == "/app/"
    cookie = back.headers["set-cookie"]
    assert "ticket_session=" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    me = api.get("/v1/me")
    assert me.json()["user_id"] == "usr-camille" and len(me.json()["memberships"]) == 2
    assert me.headers["cache-control"] == "no-store"


def test_the_server_keeps_only_a_hash_of_the_cookie_and_an_encrypted_refresh_token(
    api, provider, conn
):
    sign_in(api, provider)
    value = api.cookies["ticket_session"]
    row = conn.execute("SELECT * FROM sessions").fetchone()
    assert value not in str(row.values())
    assert row["refresh_token_encrypted"] is not None


def test_a_callback_with_an_unknown_or_used_state_fails(api, provider):
    start = api.get("/auth/login", follow_redirects=False)
    chosen = provider.post(
        follow(start.headers["location"]), data={"user": "usr-sam"}, follow_redirects=False
    )
    back = follow(chosen.headers["location"])
    assert api.get(back, follow_redirects=False).status_code == 302
    again = api.get(back, follow_redirects=False)  # the same state a second time
    assert again.status_code == 400 and again.json()["error"]["code"] == "login_failed"
    forged = api.get("/auth/callback?state=made-up&code=x", follow_redirects=False)
    assert forged.status_code == 400


def test_return_to_cannot_send_you_to_another_site(api, provider):
    back = sign_in(api, provider, return_to="https://evil.example/")
    assert back.headers["location"] == "/app/"


def test_a_change_with_the_cookie_needs_the_csrf_token(api, provider):
    sign_in(api, provider)
    refused = api.post("/auth/logout")
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "csrf_failed"
    assert api.post("/auth/logout", headers=csrf(api)).status_code == 200


def test_logout_ends_the_session_and_revokes_the_refresh_token(api, provider, conn):
    sign_in(api, provider)
    old = api.cookies["ticket_session"]
    body = api.post("/auth/logout", headers=csrf(api)).json()
    assert body["provider_logout_url"].startswith(f"{ISSUER}/logout?")
    api.cookies.set("ticket_session", old)  # someone kept a copy of the cookie
    response = api.get("/v1/me")
    assert response.status_code == 401 and response.json()["error"]["code"] == "session_ended"
    assert "logout" in response.json()["error"]["message"]
    state = provider.app.state.oauth
    assert state.revoked_families  # the provider will not refresh it any more


@pytest.mark.parametrize(
    "change, reason",
    [
        ("last_seen_at = now() - interval '31 minutes'", "idle_timeout"),
        ("expires_at = now() - interval '1 second'", "absolute_timeout"),
    ],
)
def test_a_session_ends_when_idle_or_too_old(api, provider, conn, change, reason):
    sign_in(api, provider)
    conn.execute(f"UPDATE sessions SET {change}")
    response = api.get("/v1/me")
    assert response.status_code == 401 and reason in response.json()["error"]["message"]


def test_the_session_asks_the_provider_again_when_the_access_token_is_old(api, provider, conn):
    sign_in(api, provider)
    conn.execute("UPDATE sessions SET access_expires_at = now() - interval '1 minute'")
    assert api.get("/v1/me").status_code == 200  # refreshed: a new access expiry
    row = conn.execute("SELECT access_expires_at FROM sessions").fetchone()
    assert row["access_expires_at"] > datetime.now(UTC) + timedelta(minutes=9)


def test_a_disabled_account_loses_the_session_at_the_next_refresh(api, provider, conn, idp_store):
    sign_in(api, provider, "usr-omar")
    idp_store.set_disabled("usr-omar", True)
    try:
        assert api.get("/v1/me").status_code == 200  # the access time is not over yet
        conn.execute("UPDATE sessions SET access_expires_at = now() - interval '1 second'")
        response = api.get("/v1/me")
        assert response.status_code == 401 and "provider_refused" in response.text
    finally:
        idp_store.set_disabled("usr-omar", False)


def test_account_switching_starts_a_new_session_for_the_other_person(api, provider):
    sign_in(api, provider, "usr-sam")
    sams_cookie = api.cookies["ticket_session"]
    api.post("/auth/logout", headers=csrf(api))
    # Without prompt=select_account the provider would sign Sam in again, silently.
    silent = api.get("/auth/login", follow_redirects=False)
    page = provider.get(follow(silent.headers["location"]), follow_redirects=False)
    assert page.status_code == 302  # the provider still remembers Sam
    back = sign_in(api, provider, "usr-ines", prompt="select_account")
    assert back.status_code == 302
    assert api.get("/v1/me").json()["user_id"] == "usr-ines"
    assert api.cookies["ticket_session"] != sams_cookie
    api.cookies.set("ticket_session", sams_cookie)
    assert api.get("/v1/me").status_code == 401


def test_the_page_and_the_session_answer_are_not_cached(api, provider):
    assert api.get("/app/").headers["cache-control"] == "no-store"
    assert api.get("/auth/session").json() == {"signed_in": False}
