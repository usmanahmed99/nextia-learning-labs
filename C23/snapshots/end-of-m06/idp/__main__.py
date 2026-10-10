"""The practice identity provider's commands.

    python -m idp init                 make the signing key and the client secrets (once)
    python -m idp                      run the provider on http://localhost:8400 (Ctrl+C stops it)
    python -m idp keys                 list the keys: which one signs, which ones are published
    python -m idp rotate-key [--activate]   add a new key (published; --activate: signs from now)
    python -m idp activate-key KID     sign new tokens with this published key
    python -m idp retire-key KID       stop publishing an old key
    python -m idp disable usr-sam      the person cannot sign in or refresh any more
    python -m idp enable usr-sam
    python -m idp users

Settings (environment or .env): IDP_ISSUER (http://localhost:8400), IDP_PORT (8400),
IDP_ACCESS_TOKEN_SECONDS (600), IDP_REFRESH_TOKEN_SECONDS (28800), IDP_DIR (.idp).
"""

import argparse
import os
import re
import sys
from pathlib import Path

from idp.store import ROOT, Store


def load_env() -> None:
    from dotenv import load_dotenv

    load_dotenv(Path.cwd() / ".env", override=False)


def save_secret(name: str, value: str) -> str:
    """Put NAME=value into the project's .env (made from .env.example if it is missing)."""
    env = ROOT / ".env"
    text = env.read_text(encoding="utf-8") if env.exists() else ""
    line = f"{name}={value}"
    if re.search(rf"^{name}=.*$", text, flags=re.M):
        text = re.sub(rf"^{name}=.*$", line, text, flags=re.M)
    else:
        text += ("" if text.endswith("\n") or not text else "\n") + line + "\n"
    env.write_text(text, encoding="utf-8")
    return str(env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m idp", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command")
    init = sub.add_parser("init", help="make the keys and the client secrets")
    init.add_argument("--force", action="store_true", help="start again: new keys, new secrets")
    sub.add_parser("serve", help="run the provider (the default)")
    sub.add_parser("keys")
    rotate = sub.add_parser("rotate-key")
    rotate.add_argument("--activate", action="store_true")
    for name in ("activate-key", "retire-key"):
        sub.add_parser(name).add_argument("kid")
    for name in ("disable", "enable"):
        sub.add_parser(name).add_argument("user")
    sub.add_parser("users")
    args = parser.parse_args(argv)
    load_env()
    store = Store()
    command = args.command or "serve"

    if command == "init":
        if store.exists() and not args.force:
            print(f"The provider is already set up in {store.folder}. Use --force to start again.")
            return 0
        new = store.init()
        print(f"Made a signing key ({store.keys()['active']}) and the clients in {store.folder}.")
        where = save_secret("OIDC_CLIENT_SECRET", new["help-desk-web"])
        save_secret("WORKER_CLIENT_SECRET", new["export-worker"])
        print(f"Wrote the client secrets of help-desk-web and export-worker to {where}.")
        if not os.environ.get("SESSION_KEY"):
            from cryptography.fernet import Fernet

            save_secret("SESSION_KEY", Fernet.generate_key().decode())
            print("Wrote a new SESSION_KEY (the API encrypts its sessions' tokens with it).")
        print("The provider keeps only their SHA-256. Never commit .env or .idp/.")
        return 0
    if not store.exists():
        print("The provider has no keys yet. Run: python -m idp init", file=sys.stderr)
        return 1
    if command == "serve":
        import uvicorn

        from idp.app import create_app

        issuer = os.environ.get("IDP_ISSUER", "http://localhost:8400")
        app = create_app(
            store,
            issuer=issuer,
            access_seconds=int(os.environ.get("IDP_ACCESS_TOKEN_SECONDS", "600")),
            refresh_seconds=int(os.environ.get("IDP_REFRESH_TOKEN_SECONDS", str(8 * 3600))),
        )
        print(f"Practice identity provider: {issuer} (made-up people, no passwords)")
        uvicorn.run(
            app,
            host=os.environ.get("IDP_HOST", "127.0.0.1"),
            port=int(os.environ.get("IDP_PORT", "8400")),
            log_level="warning",
        )
        return 0
    if command == "keys":
        keys = store.keys()
        for kid in keys["published"]:
            print(f"{kid}  published{'  signs new tokens' if kid == keys['active'] else ''}")
        return 0
    if command == "rotate-key":
        kid = store.new_key()
        if args.activate:
            store.activate(kid)
        print(
            f"New key {kid}: published"
            + (
                ", signs new tokens from now."
                if args.activate
                else f". Activate it later: python -m idp activate-key {kid}"
            )
        )
        return 0
    if command == "activate-key":
        store.activate(args.kid)
        print(f"Key {args.kid} signs new tokens from now.")
        return 0
    if command == "retire-key":
        store.retire(args.kid)
        print(f"Key {args.kid} is no longer published. Tokens signed with it now fail.")
        return 0
    if command in ("disable", "enable"):
        try:
            store.set_disabled(args.user, command == "disable")
        except KeyError:
            print(f"No user {args.user}.", file=sys.stderr)
            return 1
        print(
            f"{args.user} is {command}d: "
            + (
                "they cannot sign in or refresh tokens. Tokens "
                "already issued stay valid until they expire."
                if command == "disable"
                else "they can sign in."
            )
        )
        return 0
    if command == "users":
        for u in store.users().values():
            print(
                f"{u['sub']:<12} {u['name']:<8} {u['email']:<28}"
                f"{' disabled' if u['disabled'] else ''}"
            )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
