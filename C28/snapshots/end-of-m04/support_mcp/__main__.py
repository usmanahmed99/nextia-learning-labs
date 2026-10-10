"""Start the server.

    python -m support_mcp            local: stdio (an AI application starts this process)

stdio: stdout carries only MCP messages. Everything else (logs) goes to stderr.
"""

import sys


def main() -> int:
    from support_mcp.server import build_server

    build_server().run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
