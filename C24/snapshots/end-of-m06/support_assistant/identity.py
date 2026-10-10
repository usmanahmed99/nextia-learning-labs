"""A mock identity provider and the server-side permission check, aligned with the authentication course.

The identity provider is local and made up. It signs an access token as an RS256 JWT, with an
issuer, an audience (`support-assistant`), a `sub` (a stable user ID) and a short expiry. The token
carries **no tenant and no role**. The server checks the signature, the issuer, the audience and the
expiry, and then derives the tenant and the role from its **own** membership table for the tenant in
the request. A caller cannot raise their own role by changing the token.

The keys are generated once and kept in work/identity/ so that a token survives a restart. They are
made up and used only by this practice app.
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from .data import WORK

ISSUER = "https://id.localtest.example"
AUDIENCE = "support-assistant"
KEY_DIR = WORK / "identity"


class AuthError(Exception):
    """The token is missing, wrong or expired, or the user has no membership in this tenant."""


def _keys() -> tuple[str, str]:
    """Return (private PEM, public PEM), making them once."""
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    priv_path, pub_path = KEY_DIR / "private.pem", KEY_DIR / "public.pem"
    if not priv_path.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                                serialization.PrivateFormat.PKCS8,
                                                serialization.NoEncryption()))
        pub_path.write_bytes(key.public_key().public_bytes(serialization.Encoding.PEM,
                                                            serialization.PublicFormat.SubjectPublicKeyInfo))
    return priv_path.read_text(), pub_path.read_text()


def issue_token(sub: str, expires_in: int = 600, scopes: str = "tickets:read tickets:write") -> str:
    """The identity provider issues an access token for a user. No tenant and no role inside."""
    priv, _ = _keys()
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": sub, "iat": now, "exp": now + expires_in, "scope": scopes}
    return jwt.encode(claims, priv, algorithm="RS256")


def verify_token(token: str) -> dict:
    """Check the signature, issuer, audience and expiry. Return the claims, or raise AuthError."""
    _, pub = _keys()
    try:
        return jwt.decode(token, pub, algorithms=["RS256"], audience=AUDIENCE, issuer=ISSUER,
                          options={"require": ["exp", "iss", "aud", "sub"]})
    except jwt.PyJWTError as e:
        raise AuthError(f"The access token is not valid: {e}") from e


@dataclass(frozen=True)
class Session:
    """What the server decided about one caller, for one request, from its own tables."""
    sub: str
    tenant: str
    role: str                 # owner, staff, read_only
    platform_admin: bool = False

    def may_write(self) -> bool:
        return self.role in ("owner", "staff")

    def refund_limit(self) -> float:
        """The most a refund may be without the shop owner. Read-only members may not refund at all."""
        return {"owner": 100000.0, "staff": 100.0, "read_only": 0.0}[self.role]


def authorize(token: str, tenant: str, world) -> Session:
    """Turn a token and the requested tenant into a Session, using the server's membership table."""
    claims = verify_token(token)
    sub = claims["sub"]
    role = world.role_in(sub, tenant)
    if role is None:
        raise AuthError(f"{sub} has no membership in {tenant}: access refused.")
    return Session(sub=sub, tenant=tenant, role=role, platform_admin=world.is_platform_admin(sub))
