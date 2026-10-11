"""The provider's signing key and the tokens it signs."""

import json
import os
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parent.parent
ISSUER = os.environ.get("IDP_ISSUER", "http://127.0.0.1:8400")
ACCESS_TOKEN_SECONDS = int(os.environ.get("IDP_ACCESS_TOKEN_SECONDS", "600"))
ACCESS_TOKEN_TYPE = "at+jwt"  # RFC 9068: an access token says that it is one


def key_dir() -> Path:
    return Path(os.environ.get("IDP_DIR", ROOT / ".idp"))


def init(force: bool = False) -> str:
    """Make a signing key in .idp/ (git-ignored). Returns its key ID."""
    d = key_dir()
    d.mkdir(parents=True, exist_ok=True)
    if (d / "key.json").exists() and not force:
        return json.loads((d / "key.json").read_text())["kid"]
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    kid = uuid.uuid4().hex[:16]
    (d / "private.pem").write_bytes(pem)
    os.chmod(d / "private.pem", 0o600)
    (d / "key.json").write_text(json.dumps({"kid": kid}))
    return kid


def _private():
    d = key_dir()
    if not (d / "key.json").exists():
        init()
    kid = json.loads((d / "key.json").read_text())["kid"]
    return kid, serialization.load_pem_private_key((d / "private.pem").read_bytes(), password=None)


def jwks() -> dict:
    kid, private = _private()
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    return {"keys": [jwk | {"kid": kid, "use": "sig", "alg": "RS256"}]}


def access_token(
    sub: str,
    scope: str,
    audience: str,
    client_id: str = "support-host",
    seconds: int | None = None,
    now: float | None = None,
    **extra,
) -> str:
    """An access token for one resource (audience = the MCP server's URL). It names the user (sub)
    and what the application may do (scope). No organization and no role: the server takes
    those from its own membership table."""
    kid, private = _private()
    now = int(now if now is not None else time.time())
    claims = {
        "iss": ISSUER,
        "sub": sub,
        "aud": audience,
        "iat": now,
        "nbf": now,
        "exp": now + (seconds if seconds is not None else ACCESS_TOKEN_SECONDS),
        "jti": uuid.uuid4().hex,
        "client_id": client_id,
        "scope": scope,
        **extra,
    }
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": kid, "typ": ACCESS_TOKEN_TYPE})
