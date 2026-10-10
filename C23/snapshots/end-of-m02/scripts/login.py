"""Sign in through the practice identity provider, step by step, and get tokens.

    python -m scripts.login --user usr-sam               the authorization code flow with PKCE
    python -m scripts.login --user usr-sam --print-access-token     only the access token
    python -m scripts.login --user usr-sam --wrong-verifier         PKCE with the wrong verifier
    python -m scripts.login --user usr-sam --reuse-code             send the same code twice
    python -m scripts.login --refresh usr-sam            swap the saved refresh token for new tokens
    python -m scripts.login --service                    a background service's own token

It plays the browser and a command-line application ("ticket-cli", a public client: it
has no secret, so it uses PKCE). The provider must be running: python -m idp
The tokens are saved in .tokens/<user>.json (git-ignored) for the next commands.
"""

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import jwt

from ticket_api.config import load_env

CLIENT_ID = "ticket-cli"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPE = "openid profile email offline_access tickets:read tickets:write members:manage"
TOKENS = Path(".tokens")


def short(token: str, n: int = 24) -> str:
    return f"{token[:n]}...({len(token)} characters)"


def claims(token: str) -> dict:
    """The token's claims WITHOUT checking it: only to look. The API checks (ticket_api/auth.py)."""
    return jwt.decode(token, options={"verify_signature": False})


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)  # a one-time secret that stays here
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).decode().rstrip("=")


def save(user: str, body: dict) -> Path:
    TOKENS.mkdir(exist_ok=True)
    path = TOKENS / f"{user}.json"
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path


def sign_in(issuer: str, user: str, quiet: bool, wrong_verifier: bool, reuse_code: bool) -> dict:
    say = (lambda *a: None) if quiet else print
    verifier, challenge = pkce_pair()
    state, nonce = secrets.token_urlsafe(16), secrets.token_urlsafe(16)
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    with httpx.Client(base_url=issuer, timeout=10, follow_redirects=False) as http:
        say("1. The application makes a PKCE pair and sends you to the provider's sign-in page:")
        say(f"   code_verifier  {short(verifier, 12)}  (stays in the application)")
        say(f"   code_challenge {challenge}  (SHA-256 of the verifier, sent now)")
        page = http.get("/authorize", params=params)
        if page.status_code != 200:
            raise SystemExit(f"The provider refused the request: {page.text}")
        say(f"   GET {issuer}/authorize?{urlencode(params)[:90]}...  -> {page.status_code}")
        say(f"2. You pick {user} on the page. The provider sends the browser back with a code:")
        chosen = http.post("/authorize", params=params, data={"user": user})
        if chosen.status_code != 302:
            raise SystemExit(f"Sign-in failed: {chosen.status_code} {chosen.text}")
        location = chosen.headers["location"]
        query = parse_qs(urlparse(location).query)
        say(f"   302 Location: {location[:70]}...")
        if query.get("state") != [state]:
            raise SystemExit("The state is not the one we sent: stop (a forged redirect?).")
        say("   The state matches the one we sent.")
        code = query["code"][0]
        say("3. The application swaps the code and the verifier for tokens (POST /token):")
        form = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": pkce_pair()[0] if wrong_verifier else verifier,
        }
        response = http.post("/token", data=form)
        if reuse_code and response.status_code == 200:
            say("   200: tokens. Now the same code again:")
            response = http.post("/token", data=form)
        if response.status_code != 200:
            say(f"   {response.status_code} {response.json()}")
            raise SystemExit(1)
        body = response.json()
    id_claims = claims(body["id_token"])
    if id_claims.get("nonce") != nonce:
        raise SystemExit("The ID token's nonce is not ours: stop.")
    say(f"   200: token_type {body['token_type']}, expires_in {body['expires_in']} s,")
    say(f"   access_token  {short(body['access_token'])}")
    say(f"   id_token      {short(body['id_token'])}")
    say(f"   refresh_token {short(body['refresh_token'], 8)}")
    return body


def show(body: dict) -> None:
    for name in ("id_token", "access_token"):
        if name in body:
            header = jwt.get_unverified_header(body[name])
            print(f"\n{name} (decoded, not checked):")
            print(f"  header {json.dumps(header)}")
            print("  claims " + json.dumps(claims(body[name]), indent=2).replace("\n", "\n  "))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--user", help="the made-up person to sign in as, for example usr-sam")
    who.add_argument("--refresh", metavar="USER", help="use the saved refresh token of USER")
    who.add_argument("--service", action="store_true", help="the export worker's own token")
    parser.add_argument("--print-access-token", action="store_true")
    parser.add_argument("--wrong-verifier", action="store_true")
    parser.add_argument("--reuse-code", action="store_true")
    args = parser.parse_args(argv)
    load_env()
    issuer = os.environ.get("OIDC_ISSUER", "http://localhost:8400")
    quiet = args.print_access_token
    try:
        if args.user:
            body = sign_in(issuer, args.user, quiet, args.wrong_verifier, args.reuse_code)
            name = args.user
        elif args.refresh:
            name = args.refresh
            saved = json.loads((TOKENS / f"{name}.json").read_text(encoding="utf-8"))
            response = httpx.post(
                f"{issuer}/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                    "refresh_token": saved["refresh_token"],
                },
            )
            if response.status_code != 200:
                print(f"{response.status_code} {response.json()}", file=sys.stderr)
                return 1
            body = response.json()
            if not quiet:
                print("New tokens. The old refresh token cannot be used again (rotation).")
        else:
            name = "export-worker"
            response = httpx.post(
                f"{issuer}/token",
                data={"grant_type": "client_credentials", "scope": "tickets:read"},
                auth=("export-worker", os.environ.get("WORKER_CLIENT_SECRET", "")),
            )
            if response.status_code != 200:
                print(f"{response.status_code} {response.json()}", file=sys.stderr)
                return 1
            body = response.json()
    except httpx.ConnectError:
        print(f"The provider does not answer at {issuer}. Start it: python -m idp", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"No saved tokens for {args.refresh}. Sign in first.", file=sys.stderr)
        return 1
    path = save(name, body)
    if args.print_access_token:
        print(body["access_token"])
        return 0
    show(body)
    print(f"\nSaved in {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
