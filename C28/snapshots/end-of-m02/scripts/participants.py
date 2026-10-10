"""Who does what? This script is the HOST (an application). Inside it, the SDK's Client is the
MCP CLIENT. It starts the SERVER (examples/hello_server.py) as a child process and talks to it.

    python -m scripts.participants
"""

import os
import sys

import anyio
from mcp import Client, StdioServerParameters


async def main() -> None:
    server = StdioServerParameters(command=sys.executable, args=["-m", "examples.hello_server"])
    print(f"host:   this script (process {os.getpid()})")
    async with Client(server) as client:
        print(f"client: the SDK's Client, protocol {client.protocol_version}")
        info = client.server_info
        print(f"server: {info.name} {info.version}, a child process that talks on stdin/stdout")
        tools = await client.list_tools()
        for t in tools.tools:
            print(f"        tool {t.name}: {t.description}")
        result = await client.call_tool("hello", {"name": "Amira"})
        print(f"call:   hello(name='Amira') -> {result.content[0].text}")


if __name__ == "__main__":
    anyio.run(main)
