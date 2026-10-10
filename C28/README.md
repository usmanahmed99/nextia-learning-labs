# MCP: Connect AI Applications to Tools and Data

Files for the course [MCP: Connect AI Applications to Tools and Data](https://learning.nextia-ai.com/courses/mcp/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project `support-mcp`: `start` (download it in the first lesson) and the project at the end of each module. Code MIT; data CC0. |
| [`data/`](data) | The synthetic support data of Larkfield and Bramble Books (policy documents, tickets, people, memberships) with a [dataset card](data/dataset.md), and the recorded MCP message traces that the lessons show ([`data/traces/`](data/traces)). CC0. |

You need no account, no key and no money. The MCP server, the AI application (with a mock model), the practice identity provider and the tests all run on your computer. A real model is optional: your own key for an OpenAI-compatible API, or a local model server.

## Versions

The project uses **MCP specification revision 2026-07-28** and the **official MCP Python SDK 2.3.0**. MCP Inspector 2.10.1 (Node.js 22.19 or later) was used for inspection. Older tutorials may use other revisions and an older SDK: check the version before you copy code.

## Tested

Tested with Python 3.12 on macOS (Apple silicon): every snapshot, in a new virtual environment, passes its lint and its tests, and the stage's first commands run. Windows and Linux are not tested; the commands for them are in each snapshot's README.
