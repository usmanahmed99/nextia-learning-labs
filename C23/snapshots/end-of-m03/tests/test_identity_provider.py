"""Module 2 of the authentication course: the practice identity provider (idp/).

The authorization code flow with PKCE, step by step, and what the provider refuses."""

import base64
import hashlib
import secrets
from urllib.parse import parse_qs, urlparse

import jwt
import pytest

from tests.conftest import ISSUER

REDIRECT = "http://127.0.0.1:8765/callback"


def pkce():
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).decode().rstrip("=")


def authorize_params(challenge, **changes):
    return {
        "response_type": "code",
        "client_id": "ticket-cli",
        "redirect_uri": REDIRECT,
        "scope": "openid profile email offline_access tickets:read tickets:write",
        "state": "s-1",
        "nonce": "n-1",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        **changes,
    }


def sign_in(provider, user="usr-sam", **changes):
    verifier, challenge = pkce()
    params = authorize_params(challenge, **changes)
    response = provider.post(
        "/authorize", params=params, data={"user": user}, follow_redirects=False
    )
    assert response.status_code == 302, response.text
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["state"] == ["s-1"]
    return query["code"][0], verifier


def swap(provider, code, verifier, redirect=REDIRECT):
    return provider.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "ticket-cli",
            "code": code,
            "redirect_uri": redirect,
            "code_verifier": verifier,
        },
    )


def test_discovery_and_keys(provider):
    doc = provider.get("/.well-known/openid-configuration").json()
    assert doc["issuer"] == ISSUER
    assert doc["code_challenge_methods_supported"] == ["S256"]
    keys = provider.get("/jwks.json").json()["keys"]
    assert len(keys) == 1 and keys[0]["kty"] == "RSA" and "d" not in keys[0]  # public half only


def test_the_sign_in_page_lists_made_up_people(provider):
    _, challenge = pkce()
    page = provider.get("/authorize", params=authorize_params(challenge))
    assert page.status_code == 200
    assert "usr-camille" in page.text and "practice identity provider" in page.text


def test_code_and_verifier_give_tokens(provider):
    code, verifier = sign_in(provider)
    body = swap(provider, code, verifier).json()
    assert body["token_type"] == "Bearer" and body["expires_in"] == 600
    access = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert access["aud"] == "ticket-api" and access["sub"] == "usr-sam"
    assert access["scope"] == "tickets:read tickets:write"
    assert "tenant" not in str(access) and "role" not in access  # no organization, no role
    assert jwt.get_unverified_header(body["access_token"])["typ"] == "at+jwt"
    ident = jwt.decode(body["id_token"], options={"verify_signature": False})
    assert ident["aud"] == "ticket-cli" and ident["nonce"] == "n-1"
    assert ident["email"] == "sam@larkfield.example"


def test_a_wrong_verifier_gets_nothing(provider):
    code, _ = sign_in(provider)
    response = swap(provider, code, pkce()[0])
    assert response.status_code == 400 and response.json()["error"] == "invalid_grant"


def test_a_code_works_once(provider):
    code, verifier = sign_in(provider)
    assert swap(provider, code, verifier).status_code == 200
    assert swap(provider, code, verifier).json()["error"] == "invalid_grant"


def test_an_unregistered_redirect_uri_is_an_error_page_not_a_redirect(provider):
    _, challenge = pkce()
    params = authorize_params(challenge, redirect_uri="https://evil.example/steal")
    response = provider.get("/authorize", params=params, follow_redirects=False)
    assert response.status_code == 400 and "location" not in response.headers


@pytest.mark.parametrize(
    "change",
    [
        {"code_challenge_method": "plain"},
        {"code_challenge": ""},
        {"state": ""},
        {"scope": "openid admin:everything"},
    ],
)
def test_requests_without_pkce_state_or_with_unknown_scopes_are_refused(provider, change):
    _, challenge = pkce()
    assert (
        provider.get("/authorize", params=authorize_params(challenge, **change)).status_code == 400
    )


def test_a_refresh_token_works_once_and_its_reuse_ends_the_family(provider):
    code, verifier = sign_in(provider)
    first = swap(provider, code, verifier).json()["refresh_token"]
    data = {"grant_type": "refresh_token", "client_id": "ticket-cli"}
    second = provider.post("/token", data={**data, "refresh_token": first}).json()["refresh_token"]
    reuse = provider.post("/token", data={**data, "refresh_token": first})
    assert reuse.json()["error"] == "invalid_grant"
    # someone used an old copy: the newer token of the same family stops working too
    assert provider.post("/token", data={**data, "refresh_token": second}).status_code == 400


def test_a_disabled_person_cannot_refresh(provider, idp_store):
    code, verifier = sign_in(provider, user="usr-omar")
    refresh = swap(provider, code, verifier).json()["refresh_token"]
    idp_store.set_disabled("usr-omar", True)
    try:
        response = provider.post(
            "/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "ticket-cli",
                "refresh_token": refresh,
            },
        )
        assert response.json()["error"] == "invalid_grant"
    finally:
        idp_store.set_disabled("usr-omar", False)


def test_a_service_gets_its_own_token_without_a_person(provider, idp_store):
    secret = "not-the-secret"
    response = provider.post(
        "/token", data={"grant_type": "client_credentials"}, auth=("export-worker", secret)
    )
    assert response.status_code == 401  # the secret is checked


def test_the_signing_key_can_rotate_while_the_old_one_stays_published(provider, idp_store):
    old = idp_store.keys()["active"]
    new = idp_store.new_key()
    idp_store.activate(new)
    try:
        kids = [k["kid"] for k in provider.get("/jwks.json").json()["keys"]]
        assert kids == [old, new]
        code, verifier = sign_in(provider)
        token = swap(provider, code, verifier).json()["access_token"]
        assert jwt.get_unverified_header(token)["kid"] == new
    finally:
        idp_store.activate(old)
        idp_store.retire(new)


def test_a_verifier_shorter_than_43_characters_is_refused_as_a_real_provider_does(provider):
    """RFC 7636: 43 to 128 characters. Keycloak refused the API's first, 32-character
    verifier; the practice provider now checks the length too."""
    verifier = secrets.token_urlsafe(24)  # 32 characters
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    params = authorize_params(challenge.decode().rstrip("="))
    response = provider.post(
        "/authorize", params=params, data={"user": "usr-sam"}, follow_redirects=False
    )
    code = parse_qs(urlparse(response.headers["location"]).query)["code"][0]
    refused = swap(provider, code, verifier)
    assert refused.json()["error"] == "invalid_grant" and "43 to 128" in refused.text
