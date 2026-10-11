"""The practice identity provider: metadata, registration, the code flow with PKCE, one-time codes."""

import base64
import hashlib
import secrets
import urllib.parse

import httpx2
import jwt
import pytest

from idp import app as idp_app
from idp import keys
from tests.conftest import Served, free_port

RESOURCE = "http://127.0.0.1:8000/mcp"


@pytest.fixture
def provider():
    port = free_port()
    with Served(idp_app.app, port):
        yield f"http://127.0.0.1:{port}"


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def sign_in(base, user="usr-sam", resource=RESOURCE):
    client = httpx2.post(
        f"{base}/register", json={"redirect_uris": ["http://127.0.0.1:8765/callback"], "client_name": "test"}
    ).json()
    verifier, challenge = pkce()
    q = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": "http://127.0.0.1:8765/callback",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": "knowledge:read tickets:read",
        "resource": resource,
        "state": "s1",
        "login_hint": user,
    }
    r = httpx2.get(f"{base}/authorize", params=q)
    return client, verifier, r


def test_metadata_names_the_endpoints(provider):
    m = httpx2.get(f"{provider}/.well-known/oauth-authorization-server").json()
    assert m["issuer"] == keys.ISSUER and m["code_challenge_methods_supported"] == ["S256"]


def test_the_code_flow_gives_a_token_for_one_resource(provider):
    client, verifier, r = sign_in(provider)
    assert r.status_code == 302
    code = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)["code"][0]
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client["client_id"],
        "redirect_uri": "http://127.0.0.1:8765/callback",
        "code_verifier": verifier,
        "resource": RESOURCE,
    }
    t = httpx2.post(f"{provider}/token", data=form).json()
    claims = jwt.decode(t["access_token"], options={"verify_signature": False})
    assert claims["aud"] == RESOURCE and claims["sub"] == "usr-sam" and "tenant" not in claims and "role" not in claims
    again = httpx2.post(f"{provider}/token", data=form)  # a code works once
    assert again.status_code == 400 and again.json()["error"] == "invalid_grant"


def test_a_wrong_verifier_is_refused(provider):
    client, _, r = sign_in(provider)
    code = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)["code"][0]
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client["client_id"],
        "redirect_uri": "http://127.0.0.1:8765/callback",
        "code_verifier": "x" * 50,
    }
    assert httpx2.post(f"{provider}/token", data=form).json()["error_description"] == "Invalid code verifier."


def test_an_unknown_resource_is_refused(provider):
    _, _, r = sign_in(provider, resource="http://127.0.0.1:9999/other")
    assert r.status_code == 400 and r.json()["error"] == "invalid_target"
