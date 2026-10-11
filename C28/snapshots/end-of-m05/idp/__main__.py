"""python -m idp [init | serve | token | users]

python -m idp init                    make the signing key in .idp/ (once)
python -m idp                         start the provider on http://127.0.0.1:8400
python -m idp token --user usr-sam    print an access token (a practice shortcut: no sign-in)
    [--scope "knowledge:read tickets:read"] [--audience http://127.0.0.1:8000/mcp] [--seconds 600]
python -m idp users                   the made-up people
"""

import argparse
import os
import sys

from idp import app as idp_app
from idp import keys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m idp")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("init")
    sub.add_parser("serve")
    sub.add_parser("users")
    t = sub.add_parser("token")
    t.add_argument("--user", required=True)
    t.add_argument("--scope", default="knowledge:read tickets:read")
    t.add_argument("--audience", default=os.environ.get("MCP_RESOURCE_URL", "http://127.0.0.1:8000/mcp"))
    t.add_argument("--seconds", type=int, default=None)
    a = p.parse_args(argv)
    if a.cmd == "init":
        print(f"Signing key {keys.init()} in {keys.key_dir()}")
        return 0
    if a.cmd == "users":
        for u, n in idp_app.users().items():
            print(f"{u}  {n}")
        return 0
    if a.cmd == "token":
        print(keys.access_token(a.user, a.scope, a.audience, seconds=a.seconds))
        return 0
    import uvicorn

    keys.init()
    port = int(os.environ.get("IDP_PORT", "8400"))
    uvicorn.run(idp_app.app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
