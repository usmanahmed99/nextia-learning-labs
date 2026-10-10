"""Check the sign-in settings of .env against the identity provider, one setting at a time.

    python -m scripts.check_identity

It asks the provider what a real misconfiguration would show: the discovery document and its
issuer, the published keys, whether the provider knows the application and its redirect
URI, and whether the client secret is right. It changes nothing. It works with the practice
provider (python -m idp) and with a real one.
"""

import base64
import hashlib
import secrets
import sys
from urllib.parse import urlparse

import httpx

from ticket_api.config import load_settings


def main() -> int:
    s = load_settings()
    problems = 0

    def report(ok: bool, text: str, fix: str = "") -> None:
        nonlocal problems
        problems += not ok
        print(
            f"  {'OK     ' if ok else 'PROBLEM'}  {text}"
            + (f"\n           {fix}" if fix and not ok else "")
        )

    print("Sign-in settings:")
    if not s.oidc_issuer:
        report(False, "OIDC_ISSUER is not set", "Set it in .env, e.g. http://localhost:8400.")
        return 1
    base = (s.oidc_internal_url or s.oidc_issuer).rstrip("/")
    try:
        doc = httpx.get(f"{base}/.well-known/openid-configuration", timeout=5).json()
    except (httpx.HTTPError, ValueError) as error:
        report(False, f"discovery at {base}: {error}", "Is the provider running? python -m idp")
        return 1
    report(
        doc.get("issuer") == s.oidc_issuer,
        f"issuer: .env says {s.oidc_issuer}, the provider says {doc.get('issuer')}",
        "They must be the same string, to the last character (a / at the end counts).",
    )
    internal = lambda url: base + url[len(s.oidc_issuer.rstrip("/")) :]  # noqa: E731
    keys = httpx.get(internal(doc["jwks_uri"]), timeout=5).json().get("keys", [])
    rs256 = [k for k in keys if k.get("kty") == "RSA" and k.get("alg", "RS256") == "RS256"]
    report(bool(rs256), f"published keys: {len(keys)} ({len(rs256)} for RS256)")
    report("S256" in doc.get("code_challenge_methods_supported", []), "the provider supports PKCE")

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    page = httpx.get(
        internal(doc["authorization_endpoint"]),
        timeout=5,
        params={
            "response_type": "code",
            "client_id": s.oidc_client_id,
            "redirect_uri": s.oidc_redirect_uri,
            "scope": "openid",
            "state": "check",
            "code_challenge": challenge.decode().rstrip("="),
            "code_challenge_method": "S256",
        },
    )
    report(
        page.status_code in (200, 302),
        f"application {s.oidc_client_id} with redirect URI {s.oidc_redirect_uri}: "
        f"{page.status_code}",
        "Register this exact redirect URI for the application at the provider.",
    )
    answer = httpx.post(
        internal(doc["token_endpoint"]),
        timeout=5,
        data={
            "grant_type": "authorization_code",
            "code": "not-a-real-code",
            "redirect_uri": s.oidc_redirect_uri,
            "code_verifier": verifier,
        },
        auth=(s.oidc_client_id, s.oidc_client_secret or ""),
    )
    error = answer.json().get("error") if answer.content else None
    report(
        error == "invalid_grant",
        f"client secret: the provider answers {error!r} to a made-up code",
        "invalid_client means the secret (OIDC_CLIENT_SECRET) is wrong or missing.",
    )
    report(
        bool(s.session_key),
        "SESSION_KEY is set",
        "Without it, every restart of the API signs everyone out.",
    )
    https = urlparse(s.oidc_redirect_uri).scheme == "https"
    report(
        https or not s.session_cookie_secure,
        f"cookie Secure={s.session_cookie_secure}, redirect URI over "
        f"{'HTTPS' if https else 'HTTP'}",
        "Safari (WebKit) does not send a Secure cookie over plain HTTP, not even to "
        "127.0.0.1: use HTTPS, or (on your own computer only) SESSION_COOKIE_SECURE=false.",
    )
    report(
        s.oidc_audience == "ticket-api",
        f"audience: {s.oidc_audience}",
        "The access tokens must name this API as their audience.",
    )
    print(f"  allowed origins (CORS): {', '.join(s.allowed_origins) or 'none (same site only)'}")
    print(f"\n{problems} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
