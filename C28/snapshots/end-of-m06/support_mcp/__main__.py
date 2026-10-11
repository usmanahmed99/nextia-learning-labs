"""Start the server.

    python -m support_mcp            local: stdio (an AI application starts this process)
    python -m support_mcp --http     remote: Streamable HTTP on http://127.0.0.1:8000/mcp

stdio: stdout carries only MCP messages. Everything else (logs) goes to stderr.
"""

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m support_mcp")
    p.add_argument("--http", action="store_true", help="serve Streamable HTTP instead of stdio")
    p.add_argument("--port", type=int, default=int(os.environ.get("MCP_PORT", "8000")))
    a = p.parse_args(argv)
    if not a.http:
        from support_mcp.server import build_server

        build_server(transport="stdio").run("stdio")
        return 0
    import uvicorn

    from support_mcp.http import build_app

    uvicorn.run(build_app(), host="127.0.0.1", port=a.port, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
