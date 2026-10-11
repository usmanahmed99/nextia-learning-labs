"""Host, client and server: the smallest server, reached by the SDK's client."""

import subprocess
import sys

import anyio
from mcp import Client

from examples.hello_server import mcp as hello_server


def test_the_client_discovers_and_calls_the_tool():
    async def go():
        async with Client(hello_server) as client:  # in-process: no child process, same messages
            tools = await client.list_tools()
            result = await client.call_tool("hello", {"name": "Amira"})
            return [t.name for t in tools.tools], result.content[0].text

    assert anyio.run(go) == (["hello"], "Hello, Amira!")


def test_the_participants_script_starts_the_server_as_a_child_process():
    out = subprocess.run(
        [sys.executable, "-m", "scripts.participants"], capture_output=True, text=True, timeout=60, check=True
    ).stdout
    assert "server: hello-server 1.0.0" in out
    assert "hello(name='Amira') -> Hello, Amira!" in out
