"""The provider's files: signing keys, registered applications (clients) and users.

Everything lives in the folder .idp/ of the project (git-ignored): the private keys and the
client secrets are made on your computer by `python -m idp init` and are never committed.
"""

import csv
import hashlib
import json
import os
import secrets
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIR = ROOT / ".idp"
USERS_CSV = ROOT / "data" / "identity" / "users.csv"

# The applications that may ask this provider for tokens. Redirect URIs must match exactly.
CLIENTS = [
    {
        # The ticket API's own browser login (Module 3): a backend, so it can keep a secret.
        "client_id": "help-desk-web",
        "name": "Help desk (web)",
        "type": "confidential",
        "grant_types": ["authorization_code", "refresh_token"],
        "redirect_uris": ["http://127.0.0.1:8000/auth/callback"],
        "post_logout_redirect_uris": ["http://127.0.0.1:8000/app/"],
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "tickets:read",
            "tickets:write",
            "members:manage",
        ],
    },
    {
        # A command-line program on your computer: public (it cannot keep a secret), so PKCE.
        "client_id": "ticket-cli",
        "name": "Ticket command line",
        "type": "public",
        "grant_types": ["authorization_code", "refresh_token"],
        "redirect_uris": ["http://127.0.0.1:8765/callback"],
        "post_logout_redirect_uris": [],
        "scopes": [
            "openid",
            "profile",
            "email",
            "offline_access",
            "tickets:read",
            "tickets:write",
            "members:manage",
        ],
    },
    {
        # A background service: no person behind it (client credentials).
        "client_id": "export-worker",
        "name": "Export worker",
        "type": "confidential",
        "grant_types": ["client_credentials"],
        "redirect_uris": [],
        "post_logout_redirect_uris": [],
        "scopes": ["tickets:read"],
    },
]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class Store:
    def __init__(self, folder: Path | None = None):
        self.folder = Path(folder or os.environ.get("IDP_DIR") or DEFAULT_DIR)

    # ---------- set up ----------

    def exists(self) -> bool:
        return (self.folder / "keys.json").exists()

    def init(self, users_csv: Path = USERS_CSV) -> dict[str, str]:
        """Make the folder: one signing key, the clients with new secrets, the users.
        Returns the new client secrets (shown once; only their SHA-256 is kept)."""
        (self.folder / "keys").mkdir(parents=True, exist_ok=True)
        self.folder.chmod(0o700)
        self._write("keys.json", {"active": None, "published": []})
        kid = self.new_key()
        self.activate(kid)
        new_secrets, clients = {}, []
        for c in CLIENTS:
            c = dict(c)
            if c["type"] == "confidential":
                secret = secrets.token_urlsafe(32)
                new_secrets[c["client_id"]] = secret
                c["secret_sha256"] = sha256(secret)
            clients.append(c)
        self._write("clients.json", clients)
        with open(users_csv, encoding="utf-8", newline="") as f:
            users = [
                {"sub": r["user_id"], "name": r["name"], "email": r["email"], "disabled": False}
                for r in csv.DictReader(f)
            ]
        self._write("users.json", users)
        return new_secrets

    # ---------- keys ----------

    def new_key(self) -> str:
        """Make an RSA key pair and publish its public half. Returns its key ID (kid)."""
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
        # The key ID: the SHA-256 thumbprint of the public key (RFC 7638), shortened.
        canonical = json.dumps({k: jwk[k] for k in ("e", "kty", "n")}, separators=(",", ":"))
        kid = jwt.utils.base64url_encode(hashlib.sha256(canonical.encode()).digest()).decode()[:16]
        pem = private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        path = self.folder / "keys" / f"{kid}.pem"
        path.write_bytes(pem)
        path.chmod(0o600)
        keys = self._read("keys.json")
        keys["published"].append(kid)
        self._write("keys.json", keys)
        return kid

    def activate(self, kid: str) -> None:
        keys = self._read("keys.json")
        if kid not in keys["published"]:
            raise ValueError(f"no published key {kid}")
        keys["active"] = kid
        self._write("keys.json", keys)

    def retire(self, kid: str) -> None:
        """Stop publishing a key. Tokens signed with it fail from then on."""
        keys = self._read("keys.json")
        if kid == keys["active"]:
            raise ValueError("this key signs new tokens: activate another key first")
        keys["published"] = [k for k in keys["published"] if k != kid]
        self._write("keys.json", keys)

    def keys(self) -> dict:
        return self._read("keys.json")

    def private_key(self, kid: str) -> bytes:
        return (self.folder / "keys" / f"{kid}.pem").read_bytes()

    def jwks(self) -> dict:
        """The public keys, as the provider publishes them at /jwks.json."""
        out = []
        for kid in self.keys()["published"]:
            private = serialization.load_pem_private_key(self.private_key(kid), password=None)
            jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
            out.append({**jwk, "kid": kid, "use": "sig", "alg": "RS256"})
        return {"keys": out}

    # ---------- clients and users ----------

    def clients(self) -> dict[str, dict]:
        return {c["client_id"]: c for c in self._read("clients.json")}

    def users(self) -> dict[str, dict]:
        return {u["sub"]: u for u in self._read("users.json")}

    def set_disabled(self, sub: str, disabled: bool) -> None:
        users = self._read("users.json")
        if not any(u["sub"] == sub for u in users):
            raise KeyError(sub)
        for u in users:
            if u["sub"] == sub:
                u["disabled"] = disabled
        self._write("users.json", users)

    # ---------- files ----------

    def _read(self, name: str):
        return json.loads((self.folder / name).read_text(encoding="utf-8"))

    def _write(self, name: str, data) -> None:
        path = self.folder / name
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(path)
