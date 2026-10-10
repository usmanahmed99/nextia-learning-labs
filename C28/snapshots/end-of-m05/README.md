# support-mcp

One MCP server that gives AI applications the support knowledge of two shops, **Larkfield** and **Bramble Books**: their policy documents and their tickets.
A small AI application (a *host*) that uses it is included.

This project belongs to the course *MCP: Connect AI Applications to Tools and Data* on Nextia Learning. Every person, ticket and shop in it is made up.

## Versions

This project uses **MCP specification revision 2026-07-28** with the **official MCP Python SDK 2.3.0** (`pip` package `mcp`). The SDK also accepts older clients that use the `initialize` handshake (revisions 2024-11-05 to 2025-11-25). Tested with Python 3.12 on macOS. If you copy MCP code from somewhere else, check which revision and SDK version it was written for first.

## What it offers

| Kind | Name | Who chooses it | What it does |
|---|---|---|---|
| Tool | `search_knowledge` | the model | Finds the best policy documents of your organization (at most 5 short matches). Read-only. |
| Tool | `get_ticket` | the model | Gets one ticket of your organization by its ID. Read-only. |
| Resource | `policy://{tenant}/{doc_id}` | the application | The full text of one policy document. |
| Prompt | `draft_reply` | you | A template: "draft a reply to this ticket using our policies". |

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
The tests start the server themselves.

## Use it

```sh
python -m support_mcp.knowledge search larkfield "return a damaged item"   # the business service alone
python -m scripts.trace discovery                                          # the MCP messages, by hand
python -m host "Draft a reply to ticket T-30002"                           # the host with a mock model
```

The host starts the server as a child process (stdio) for the person in `--user` and the organization in `--tenant` (default: Sam at Larkfield).

Inspect the server with MCP Inspector (needs Node.js 22.19 or later; it downloads the Inspector the first time):

```sh
npx @modelcontextprotocol/inspector@2.10.1 --cli python -m support_mcp -- --method tools/list
```

### Remote access (Streamable HTTP)

Three terminals, each with the virtual environment active:

```sh
python -m idp init        # once: makes a practice signing key in .idp/
python -m idp             # terminal 1: the practice identity provider, http://127.0.0.1:8400
python -m support_mcp --http   # terminal 2: the server, http://127.0.0.1:8000/mcp
```

Terminal 3 (macOS and Linux):

```sh
TOKEN=$(python -m idp token --user usr-sam)
python -m host "What is the return window?" --http http://127.0.0.1:8000/mcp --token "$TOKEN" --tenant larkfield
```

Windows (PowerShell):

```powershell
$TOKEN = python -m idp token --user usr-sam
python -m host "What is the return window?" --http http://127.0.0.1:8000/mcp --token $TOKEN --tenant larkfield
```

`python -m idp token` is a practice shortcut: it signs a token without a sign-in. The provider also runs the real sign-in flow (authorization code with PKCE) at `/authorize` and `/token`. To see the whole flow done by the SDK's own OAuth client (metadata, registration, PKCE, token), run:

```sh
python -m scripts.oauth_login
```

### A real model (optional)

The host uses a mock model unless you choose another. With your own key for any OpenAI-compatible API, or a local model server, set `MODEL_BASE_URL`, `MODEL_API_KEY` and `MODEL_NAME` (see `.env.example`) and add `--model openai`. Set a spending limit with your provider first.

## Reset

The policy documents and tickets are read from `data/` at every start and never change.
Delete `.idp/` (the practice key), then run `python -m idp init` again.

## Files

| Path | What it is |
|---|---|
| `data/` | The synthetic data and its dataset card |
| `support_mcp/knowledge.py` | The business service: search and ticket lookup inside one organization |
| `support_mcp/contracts.py` | The capability contracts: inputs, outputs, bounds, URIs, the prompt |
| `support_mcp/server.py` | The MCP server |
| `support_mcp/identity.py` | Who is the caller, in which organization, with which role and scopes |
| `support_mcp/http.py` | Streamable HTTP and the access-token check |
| `support_mcp/logs.py` | Logs on stderr (stdout is for the protocol) |
| `host/` | A minimal AI application with one MCP client and a mock model |
| `idp/` | A practice identity provider (authorization server) |
| `examples/hello_server.py` | The smallest MCP server |
| `scripts/` | Traces, versions, the attempts table, the sign-in flow, the contract, compatibility, latency |
| `docs/` | The integration map, the capability catalog, the remote design, the compatibility checklist |

## Licence

MIT (see `LICENSE`). The data is CC0 (see `data/dataset.md`).
