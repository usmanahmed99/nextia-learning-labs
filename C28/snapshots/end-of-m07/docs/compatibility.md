# Compatibility checklist

Pinned: MCP specification revision **2026-07-28**, MCP Python SDK **2.3.0**, Python 3.12. Run `python -m scripts.compat` after every change; it repeats the checks below for the SDK client rows.

Every row names its **protocol era**: **current** is revision 2026-07-28 (no handshake: `server/discover`, and `_meta` on every request); **legacy handshake** is revision 2025-11-25 (`initialize`, then `notifications/initialized`). The server speaks both, so each client is tested in each era it can use.

| Client | Transport | Era (revision) | Discovery | Valid call | Validation failure | Resource | Prompt | No token refused | How tested |
|---|---|---|---|---|---|---|---|---|---|
| MCP Python SDK 2.3.0 `Client` (`mode="auto"`) | in-process, stdio | current (2026-07-28) | pass | pass | pass | pass | pass | n/a | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` (`mode="auto"`) | Streamable HTTP | current (2026-07-28) | pass | pass | pass | pass | pass | pass | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` (`mode="legacy"`) | in-process, stdio | legacy handshake (2025-11-25) | pass | pass | pass | pass | pass | n/a | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` (`mode="legacy"`) | Streamable HTTP | legacy handshake (2025-11-25) | pass | pass | pass | pass | pass | pass | `scripts.compat` |
| MCP Python SDK 1.30.0 `ClientSession` (an older client) | stdio, Streamable HTTP | legacy handshake (2025-11-25) | pass | pass | pass | pass | pass | — | run once by hand |
| MCP Inspector 2.10.1 (CLI, its default) | stdio | legacy handshake (2025-11-25) | pass | pass | pass | pass | pass | — | run once by hand |
| MCP Inspector 2.10.1 (CLI, `--protocol-era modern`) | stdio | current (2026-07-28) | pass | pass | pass | pass | pass | — | run once by hand |
| The course's host (`python -m host`) | stdio, Streamable HTTP | current (2026-07-28); legacy handshake with `--legacy` | pass | pass | pass | — | — | pass | tests |
| Desktop assistants and code editors | — | — | not tested by the course | | | | | | configuration only |

The older revisions 2024-11-05, 2025-03-26 and 2025-06-18 use the same handshake. SDK 2.3.0 accepts them, but no client with those revisions was tested.

## Known differences

- **Unknown tool:** the specification asks for a protocol error (`-32602`); SDK 2.3.0 answers with a tool result with `isError: true` ("Unknown tool: …"). Clients must handle both.
- **Inspector's default era:** Inspector 2.10.1 uses the legacy handshake unless you pass `--protocol-era modern`. A pass with the default tests revision 2025-11-25 only.
- **Inspector CLI arguments:** `--tool-arg ticket_id=30002` sends the number 30002, not the text "30002". Quote JSON strings: `--tool-arg 'ticket_id="30002"'`.
- **Optional features** (elicitation, subscriptions, completion): not used by this server. Do not assume that a client supports them.
- **Legacy:** the HTTP+SSE transport (revision 2024-11-05) is not offered. Recognize it in old tutorials (`/sse` and `/messages` endpoints); do not build on it.
