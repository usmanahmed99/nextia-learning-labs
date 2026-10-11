# Recorded MCP message traces

Real messages between the course's `support-mcp` server and its clients, recorded on a Mac with the project at the end of the course (MCP specification revision 2026-07-28, MCP Python SDK 2.3.0). The lessons show parts of them. CC0.

| File | What it is |
|---|---|
| `raw/<name>.jsonl` | Hand-written JSON-RPC messages over stdio (`python -m scripts.trace <name>`): one line per message or log line, with the time since the start (`t_ms`), the direction (`->` client to server, `<-` server to client, `log` for stderr) and the size in bytes. |
| `host_mock.jsonl`, `host_mock_steps.json` | One request through the course's AI application with the mock model: the messages on the wire (recorded with `scripts/tee.py`) and the application's steps. |
| `host_real.jsonl`, `host_real_steps.json` | The same request with a real hosted model (chat-small, gpt-6-luna on Azure). |
| `host_timeout_steps.json`, `host_oversized_steps.json` | The application's steps when a tool is too slow (a practice delay of 5 s, a time limit of 2 s) and when a result is too large (a limit of 600 characters). |
| `http.json` | Streamable HTTP requests and answers: no token, a valid call, a token for another API, a person without a membership. The token is replaced by `[token]`. |

All people, tickets and shops are made up.
