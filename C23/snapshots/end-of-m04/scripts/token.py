"""Look inside a token, and see which check of the API refuses a bad one.

    python -m scripts.token decode <token>     header, claims and signature (decoded, NOT checked)
    python -m scripts.token decode --user usr-sam     the saved access token of usr-sam
    python -m scripts.token cases              made-up bad tokens, sent to GET /v1/me
    python -m scripts.token cases --json

`cases` makes each token with the practice provider's keys in .idp/ (python -m idp init
first) and sends it to the API code in this folder (no server needed). Every bad token is
constructed for the course: it is how a mistake or an attack would look.
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from idp.store import Store
from idp.tokens import Signer
from ticket_api.config import load_settings

ISSUER = "http://localhost:8400"
SCOPE = "tickets:read tickets:write members:manage"


def when(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def decode(token: str) -> None:
    header = jwt.get_unverified_header(token)
    body = jwt.decode(token, options={"verify_signature": False})
    head, payload, signature = token.split(".")
    print(
        f"A JWT is three parts, separated by dots: {len(head)}, {len(payload)} and "
        f"{len(signature)} characters."
    )
    print(f"1. header (base64url JSON): {json.dumps(header)}")
    print("2. claims (base64url JSON):")
    for k, v in body.items():
        extra = f"   ({when(v)})" if k in ("exp", "iat", "nbf", "auth_time") else ""
        print(f"     {k:<10} {json.dumps(v)}{extra}")
    print(f"3. signature: {signature[:16]}... ({len(jwt.utils.base64url_decode(signature))} bytes)")
    print("Decoding is not checking: anyone can read these parts. Only the signature, checked with")
    print(f"the provider's public key {header.get('kid')!r}, shows that the provider made them.")


def other_key() -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def make_cases(store: Store, issuer: str = ISSUER, now: float | None = None) -> list[dict]:
    """The made-up tokens of the course: one good token, then one mistake or attack each."""
    now = int(now or time.time())
    signer = Signer(store, issuer)
    kid = store.keys()["active"]
    own = store.private_key(kid)
    good = signer.access_token("usr-sam", "help-desk-web", SCOPE, now=now)
    claims = jwt.decode(good, options={"verify_signature": False})
    header = {"kid": kid, "typ": "at+jwt"}

    def signed(changes: dict, key: bytes = own, headers: dict = header, alg="RS256") -> str:
        return jwt.encode({**claims, **changes}, key, algorithm=alg, headers=headers)

    head, payload, sig = good.split(".")
    forged = jwt.utils.base64url_encode(
        json.dumps({**claims, "sub": "usr-grace"}, separators=(",", ":")).encode()
    ).decode()
    public = store.jwks()["keys"][0]
    users = store.users()
    return [
        {"case": "valid", "what": "Sam's access token, as the provider issued it", "token": good},
        {"case": "no_token", "what": "no Authorization header at all", "token": None},
        {
            "case": "expired",
            "what": "expired 5 minutes ago",
            "token": signed({"exp": now - 300, "iat": now - 900, "nbf": now - 900}),
        },
        {
            "case": "expired_within_leeway",
            "what": "expired 10 seconds ago (inside the 30 s leeway)",
            "token": signed({"exp": now - 10, "iat": now - 610, "nbf": now - 610}),
        },
        {
            "case": "not_yet_valid",
            "what": "valid only from 5 minutes from now (nbf)",
            "token": signed({"nbf": now + 300}),
        },
        {
            "case": "wrong_audience",
            "what": "made for another API (aud billing-api)",
            "token": signed({"aud": "billing-api"}),
        },
        {
            "case": "wrong_issuer",
            "what": "from another issuer",
            "token": signed({"iss": "http://localhost:9999"}),
        },
        {
            "case": "id_token",
            "what": "Sam's ID token sent as an access token",
            "token": signer.id_token(users["usr-sam"], "help-desk-web", "n-1", now, now=now),
        },
        {
            "case": "alg_none",
            "what": "unsigned (alg none)",
            "token": jwt.encode(
                {**claims}, None, algorithm="none", headers={"typ": "at+jwt", "kid": kid}
            ),
        },
        {
            "case": "hs256_public_key",
            "what": "HS256, with the provider's PUBLIC key as the secret",
            "token": _hs256(claims, public, kid),
        },
        {
            "case": "unknown_key",
            "what": "signed with a key the provider never published",
            "token": signed(
                {}, key=other_key(), headers={"kid": "not-a-provider-key", "typ": "at+jwt"}
            ),
        },
        {
            "case": "wrong_key_same_kid",
            "what": "signed with another key, using the provider's kid",
            "token": signed({}, key=other_key()),
        },
        {
            "case": "tampered",
            "what": "sub changed to usr-grace after signing (signature kept)",
            "token": f"{head}.{forged}.{sig}",
        },
        {
            "case": "missing_sub",
            "what": "no sub claim",
            "token": jwt.encode(
                {k: v for k, v in claims.items() if k != "sub"},
                own,
                algorithm="RS256",
                headers=header,
            ),
        },
        {"case": "not_a_jwt", "what": "a random string", "token": "abc.def"},
    ]


def _hs256(claims: dict, public_jwk: dict, kid: str) -> str:
    """The "algorithm confusion" attack: sign with HMAC, using the public key as the secret.
    PyJWT refuses to even make it with a PEM key, so the parts are put together by hand."""
    import hashlib
    import hmac

    pem = jwt.PyJWK(public_jwk).key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    enc = jwt.utils.base64url_encode
    head = enc(json.dumps({"alg": "HS256", "typ": "at+jwt", "kid": kid}).encode()).decode()
    body = enc(json.dumps(claims, separators=(",", ":")).encode()).decode()
    sig = enc(hmac.new(pem, f"{head}.{body}".encode(), hashlib.sha256).digest()).decode()
    return f"{head}.{body}.{sig}"


def run_cases(store: Store, client: TestClient) -> list[dict]:
    out = []
    for c in make_cases(store):
        headers = {"Authorization": f"Bearer {c['token']}"} if c["token"] else {}
        r = client.get("/v1/me", headers=headers)
        out.append(
            {
                "case": c["case"],
                "what": c["what"],
                "status": r.status_code,
                "check": r.headers.get("x-token-check", "passed" if r.status_code == 200 else ""),
                "code": r.json().get("error", {}).get("code") if r.status_code != 200 else None,
                "message": r.json().get("error", {}).get("message")
                if r.status_code != 200
                else None,
                "header": jwt.get_unverified_header(c["token"])
                if c["token"] and "." in c["token"] and c["case"] != "not_a_jwt"
                else None,
                "claims": _claims(c["token"]),
            }
        )
    return out


def _claims(token):
    try:
        return jwt.decode(token, options={"verify_signature": False}) if token else None
    except jwt.DecodeError:
        return None


def api_client(store: Store) -> TestClient:
    """The API in this process, with the provider's keys read straight from .idp/."""
    from dataclasses import replace

    from ticket_api.main import create_app

    settings = replace(load_settings(), oidc_issuer=ISSUER)
    app = create_app(settings)
    docs = {
        "/.well-known/openid-configuration": {"issuer": ISSUER, "jwks_uri": f"{ISSUER}/jwks.json"}
    }
    app.state.validator.provider.fetch = lambda url: (
        docs.get(url.removeprefix(ISSUER)) or store.jwks()
    )
    return TestClient(app, raise_server_exceptions=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("decode")
    d.add_argument("token", nargs="?")
    d.add_argument("--user", help="decode the saved access token of this user (.tokens/)")
    d.add_argument("--id-token", action="store_true", help="the saved ID token instead")
    c = sub.add_parser("cases")
    c.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "decode":
        token = args.token
        if args.user:
            saved = json.loads(Path(f".tokens/{args.user}.json").read_text(encoding="utf-8"))
            token = saved["id_token" if args.id_token else "access_token"]
        if not token:
            parser.error("give a token, or --user")
        decode(token)
        return 0
    store = Store()
    if not store.exists():
        print("The provider has no keys yet. Run: python -m idp init", file=sys.stderr)
        return 1
    with api_client(store) as client:
        results = run_cases(store, client)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    print("Made-up tokens sent to GET /v1/me (constructed for the course):\n")
    for r in results:
        verdict = "accepted" if r["status"] == 200 else f"refused by: {r['check'] or r['code']}"
        print(f"  {r['case']:<22} {r['status']}  {verdict:<34} {r['what']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
