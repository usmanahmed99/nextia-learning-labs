"""Run the HTTP server inside a script (a thread on a free port), with a practice key.

For scripts and tests only: no separate provider process is needed, because the server is given
the provider's public keys directly. `python -m support_mcp --http` is the real way to run it.
"""

import socket
import threading
import time
from contextlib import contextmanager

import uvicorn

from idp import keys
from support_mcp.http import JwtVerifier, build_app


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def serve_app(app, port: int):
    """Serve any ASGI app (for example the practice identity provider) on 127.0.0.1:port."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


@contextmanager
def serve_http(port: int | None = None):
    """Yields the server's URL. Tokens: keys.access_token(user, scope, url)."""
    port = port or free_port()
    url = f"http://127.0.0.1:{port}/mcp"
    app = build_app(JwtVerifier(keys.ISSUER, url, jwks=keys.jwks()), issuer=keys.ISSUER, resource_url=url)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.02)
    try:
        yield url
    finally:
        server.should_exit = True
        thread.join(timeout=10)
