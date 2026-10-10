"""A small MCP server with Larkfield's read-only order lookup (optional example).

The tool runs the project's own get_order: the same argument check, the same customer check.
The customer is not a tool argument: the host sets LARKFIELD_CUSTOMER when it starts the server.
"""

import os
import sys
from pathlib import Path

# The project: the folder in RESOLUTION_WORKFLOW (client.py sets it), else ../resolution-workflow.
PROJECT = os.environ.get("RESOLUTION_WORKFLOW") or Path(__file__).resolve().parent.parent / "resolution-workflow"
sys.path.insert(0, str(PROJECT))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from resolver.systems import World  # noqa: E402
from resolver.tools import run_read  # noqa: E402

CUSTOMER = os.environ.get("LARKFIELD_CUSTOMER", "")
DB = Path(os.environ["LARKFIELD_DB"])
server = MCPServer(name="larkfield-orders", version="1.0.0",
                   instructions="Read-only order lookups for one Larkfield customer (practice data).")


@server.tool(name="get_order", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                                           idempotentHint=True))
def get_order(order_id: str) -> str:
    """Look up one of this customer's orders by its order ID (LK- and 6 digits). Read-only."""
    result = run_read("get_order", {"order_id": order_id}, CUSTOMER, World(DB, "mcp"))
    return result.for_model()


if __name__ == "__main__":
    server.run()
