"""Write down the versions: the specification revision, the SDK, Python and what the SDK speaks.

python -m scripts.versions
"""

import platform
from importlib.metadata import version

from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_MODERN_VERSION

import support_mcp


def report() -> dict:
    return {
        "specification revision (this project)": support_mcp.SPEC_REVISION,
        "MCP Python SDK (pinned)": support_mcp.SDK_VERSION,
        "MCP Python SDK (installed)": version("mcp"),
        "newest revision the SDK speaks": LATEST_MODERN_VERSION,
        "older revisions it still accepts (initialize handshake)": ", ".join(HANDSHAKE_PROTOCOL_VERSIONS),
        "Python": platform.python_version(),
    }


def main() -> None:
    for k, v in report().items():
        print(f"{k}: {v}")
    r = report()
    if r["MCP Python SDK (installed)"] != r["MCP Python SDK (pinned)"]:
        print("WARNING: the installed SDK is not the pinned one. Run: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
