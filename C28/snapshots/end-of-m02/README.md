# support-mcp

The support knowledge of two shops, **Larkfield** and **Bramble Books**: their policy documents and their tickets. In this course it becomes one MCP server that any AI application can use.

This project belongs to the course *MCP: Connect AI Applications to Tools and Data* on Nextia Learning. Every person, ticket and shop in it is made up.

## Versions

This project uses **MCP specification revision 2026-07-28** with the **official MCP Python SDK 2.3.0** (`pip` package `mcp`). The SDK also accepts older clients that use the `initialize` handshake (revisions 2024-11-05 to 2025-11-25). Tested with Python 3.12 on macOS. If you copy MCP code from somewhere else, check which revision and SDK version it was written for first.

## Set up (once)

macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

You need no account, no key and no money.

## Use it

```sh
python -m support_mcp.knowledge search larkfield "return a damaged item"   # the business service alone
```


## Reset

The policy documents and tickets are read from `data/` at every start and never change.

## Files

| Path | What it is |
|---|---|
| `data/` | The synthetic data and its dataset card |
| `support_mcp/knowledge.py` | The business service: search and ticket lookup inside one organization |
| `support_mcp/contracts.py` | The capability contracts: inputs, outputs, bounds, URIs, the prompt |
| `examples/hello_server.py` | The smallest MCP server |
| `scripts/` | Traces, versions, the attempts table, the sign-in flow, the contract, compatibility, latency |
| `docs/` | The integration map, the capability catalog, the remote design, the compatibility checklist |

## Licence

MIT (see `LICENSE`). The data is CC0 (see `data/dataset.md`).
