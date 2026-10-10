# Compatibility checklist

Pinned: MCP specification revision **2026-07-28**, MCP Python SDK **2.3.0**, Python 3.12. Run `python -m scripts.compat` after every change; it repeats the checks below.

| Client | Transport | Protocol | Discovery | Valid call | Validation failure | Resource | Prompt | No token refused | How tested |
|---|---|---|---|---|---|---|---|---|---|
| MCP Python SDK 2.3.0 `Client` | in-process | 2026-07-28 | pass | pass | pass | pass | pass | n/a | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` | stdio | 2026-07-28 | pass | pass | pass | pass | pass | n/a | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` | Streamable HTTP | 2026-07-28 | pass | pass | pass | pass | pass | pass | `scripts.compat` |
| MCP Python SDK 2.3.0 `Client` (`mode="legacy"`) | in-process, stdio, Streamable HTTP | 2025-11-25 | pass | pass | pass | pass | pass | pass | `scripts.compat` |
| The course's host (`python -m host`) | stdio, Streamable HTTP | 2026-07-28, 2025-11-25 | pass | pass | pass | — | — | pass | tests |
| MCP Inspector 2.10.1 (CLI) | stdio | (its own choice) | pass | pass | pass | pass | pass | — | run once by hand |
| Desktop assistants and code editors | — | — | not tested by the course | | | | | | configuration only |

## Known differences

- **Unknown tool:** the specification asks for a protocol error (`-32602`); SDK 2.3.0 answers with a tool result with `isError: true` ("Unknown tool: …"). Clients must handle both.
- **Inspector CLI arguments:** `--tool-arg ticket_id=30002` sends the number 30002, not the text "30002". Quote JSON strings: `--tool-arg 'ticket_id="30002"'`.
- **Optional features** (elicitation, subscriptions, completion): not used by this server. Do not assume that a client supports them.
- **Legacy:** the HTTP+SSE transport (revision 2024-11-05) is not offered. Recognize it in old tutorials (`/sse` and `/messages` endpoints); do not build on it.
