"""Module 2, lesson 3: the API checks every access token, and says which check refused it."""

import pytest

from scripts import token as token_script

# The made-up tokens of scripts/token.py and the check that must refuse each one.
EXPECTED = {
    "valid": (200, "passed"),
    "no_token": (401, ""),
    "expired": (401, "expired"),
    "expired_within_leeway": (200, "passed"),
    "not_yet_valid": (401, "not_yet_valid"),
    "wrong_audience": (401, "wrong_audience"),
    "wrong_issuer": (401, "wrong_issuer"),
    "id_token": (401, "wrong_token_type"),
    "alg_none": (401, "algorithm_not_allowed"),
    "hs256_public_key": (401, "algorithm_not_allowed"),
    "unknown_key": (401, "unknown_key"),
    "wrong_key_same_kid": (401, "bad_signature"),
    "tampered": (401, "bad_signature"),
    "missing_sub": (401, "missing_claim"),
    "not_a_jwt": (401, "malformed"),
}


@pytest.fixture
def results(api, idp_store):
    return {r["case"]: r for r in token_script.run_cases(idp_store, api)}


def test_every_made_up_token_gets_the_expected_answer(results):
    assert {c: (r["status"], r["check"]) for c, r in results.items()} == EXPECTED


def test_a_refusal_says_why_in_the_standard_header(api, token_for):
    expired = token_for("usr-sam", exp=1, iat=0, nbf=0)
    response = api.get("/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"
    assert 'error="invalid_token"' in response.headers["www-authenticate"]


def test_without_a_token_the_api_asks_for_one(api):
    response = api.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"
    assert response.headers["www-authenticate"].startswith("Bearer")


def test_an_id_token_is_also_for_another_audience(api, idp_store):
    """Even without the typ check, the audience check would refuse an ID token."""
    from ticket_api.auth import TokenRejected

    cases = {c["case"]: c for c in token_script.make_cases(idp_store)}
    validator = api.app.state.validator
    validator.check_type = False
    with pytest.raises(TokenRejected) as refused:
        validator.validate(cases["id_token"]["token"])
    assert refused.value.code == "wrong_audience"


def test_the_keys_are_fetched_once_and_again_for_a_new_key(api, as_user, idp_store, provider):
    validator = api.app.state.validator
    for _ in range(3):
        assert api.get("/v1/me", headers=as_user("usr-sam")).status_code == 200
    assert validator.provider.fetches == 1  # cached
    old = idp_store.keys()["active"]
    new = idp_store.new_key()
    idp_store.activate(new)
    try:
        validator.provider.min_refresh_seconds = 0
        assert api.get("/v1/me", headers=as_user("usr-sam")).status_code == 200
        assert validator.provider.fetches == 2  # an unknown key ID: fetched again, once
    finally:
        idp_store.activate(old)
        idp_store.retire(new)
