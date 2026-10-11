"""The smallest MCP server: one tool. Run it with: python -m examples.hello_server (stdio)."""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("hello-server", version="1.0.0")


@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run("stdio")
