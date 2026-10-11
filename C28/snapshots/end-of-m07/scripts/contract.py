"""The server's public contract, written to contract/: every tool, resource template and prompt
as a client sees them. A test compares the server with these files after every change.

    python -m scripts.contract           show the differences (exit 1 if any)
    python -m scripts.contract --write   accept the server's current contract (review the diff first)
"""

import json
import sys
from pathlib import Path

import anyio
from mcp import Client

from support_mcp.server import build_server

OUT = Path(__file__).resolve().parent.parent / "contract" / "capabilities.json"


async def current() -> dict:
    async with Client(build_server()) as c:
        tools = (await c.list_tools()).tools
        templates = (await c.list_resource_templates()).resource_templates
        prompts = (await c.list_prompts()).prompts
        return {
            "protocol": c.protocol_version,
            "tools": [t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in tools],
            "resourceTemplates": [t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in templates],
            "prompts": [p.model_dump(mode="json", by_alias=True, exclude_none=True) for p in prompts],
        }


def main(argv: list[str]) -> int:
    now = anyio.run(current)
    text = json.dumps(now, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if "--write" in argv:
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(
            f"Wrote {OUT.name}: {len(now['tools'])} tools, {len(now['resourceTemplates'])} resource template, "
            f"{len(now['prompts'])} prompt"
        )
        return 0
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if old == text:
        print("The server matches contract/capabilities.json.")
        return 0
    import difflib

    sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), text.splitlines(True), "contract", "server"))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
