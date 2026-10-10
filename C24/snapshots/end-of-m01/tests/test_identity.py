import time

import jwt
import pytest

from support_assistant.identity import AuthError, authorize, issue_token, verify_token
from support_assistant.runner import fresh_world


def test_token_round_trip():
    claims = verify_token(issue_token("usr-grace"))
    assert claims["sub"] == "usr-grace" and claims["aud"] == "support-assistant"


def test_expired_token_is_rejected():
    token = issue_token("usr-grace", expires_in=-10)
    with pytest.raises(AuthError):
        verify_token(token)


def test_server_derives_the_role_not_the_token():
    w = fresh_world()
    # Grace is the owner at Larkfield and has no membership at Bramble.
    assert authorize(issue_token("usr-grace"), "larkfield", w).role == "owner"
    with pytest.raises(AuthError):
        authorize(issue_token("usr-grace"), "bramble", w)


def test_user_with_no_membership_sees_nothing():
    w = fresh_world()
    with pytest.raises(AuthError):
        authorize(issue_token("usr-tomas"), "larkfield", w)


def test_same_user_different_roles_in_two_tenants():
    w = fresh_world()
    assert authorize(issue_token("usr-camille"), "larkfield", w).role == "staff"
    assert authorize(issue_token("usr-camille"), "bramble", w).role == "read_only"


def test_a_token_signed_by_another_key_is_rejected():
    forged = jwt.encode({"iss": "https://id.localtest.example", "aud": "support-assistant", "sub": "usr-grace",
                         "exp": int(time.time()) + 600}, "x"*40, algorithm="HS256")
    with pytest.raises(AuthError):
        verify_token(forged)
