"""Start the MCP server, list its tools, and call get_order four times (optional example)."""

import asyncio
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_project() -> Path:
    """The course project: RESOLUTION_WORKFLOW, else ../resolution-workflow, else the labs snapshot end-of-m05."""
    candidates = [Path(os.environ["RESOLUTION_WORKFLOW"])] if os.environ.get("RESOLUTION_WORKFLOW") else []
    candidates += [HERE.parent / "resolution-workflow", HERE.parent.parent / "snapshots" / "end-of-m05"]
    for folder in candidates:
        if (folder / "resolver" / "__init__.py").exists():
            return folder.resolve()
    sys.exit("Cannot find the project resolution-workflow. Set RESOLUTION_WORKFLOW to its folder.")


PROJECT = find_project()
sys.path.insert(0, str(PROJECT))

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from resolver.data import SEED_DB  # noqa: E402
from resolver.tools import function_tools  # noqa: E402


async def main(db: Path) -> None:
    server = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")],
                                   env={**os.environ, "LARKFIELD_CUSTOMER": "C-50533", "LARKFIELD_DB": str(db),
                                        "RESOLUTION_WORKFLOW": str(PROJECT)})
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("Server:", init.server_info.name, "| protocol", init.protocol_version)
            for tool in (await session.list_tools()).tools:
                print("Tool:", tool.name, "|", tool.description)
                print("  schema:", json.dumps(tool.input_schema))
                print("  hints: ", tool.annotations.model_dump(exclude_none=True))
            calls = [{"order_id": "LK-640436"},                            # this customer's own order
                     {"order_id": "LK-615204"},                            # another customer's order
                     {"order_id": "LK-000001"},                            # an order that does not exist
                     {"order_id": "LK-640436", "customer_id": "C-20417"}]  # an extra argument
            for arguments in calls:
                result = await session.call_tool("get_order", arguments)
                print(f"Call {json.dumps(arguments)}: is_error={result.is_error}")
                print(f"  {result.content[0].text[:80]}")


db = Path(tempfile.mkdtemp(prefix="mcp-")) / "larkfield.sqlite"
shutil.copyfile(SEED_DB, db)
asyncio.run(main(db))
direct = next(t for t in function_tools() if t["function"]["name"] == "get_order")["function"]
print("Direct schema:", json.dumps(direct["parameters"]))
with sqlite3.connect(db) as con:
    print("Changes in the practice copy:", con.execute("SELECT count(*) FROM ticket_notes").fetchone()[0], "ticket note(s)")
