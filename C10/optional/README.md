# Optional examples

Two small examples for [AI Agents and Workflow Orchestration](https://learning.nextia-ai.com/courses/agents/). They are **optional. You do not need them for the course**, its checks or its certificate. Each one needs its own virtual environment with one or two extra packages. Do not install them into the project.

| Folder | Lesson | What it shows |
|---|---|---|
| [`langgraph/`](langgraph) | [Side effects and retries](https://learning.nextia-ai.com/courses/agents/m04/side-effects-and-retries/) | The course's agent loop as a LangGraph graph: the same state, a SQLite checkpointer, and `interrupt()` for the approval. It runs three things. 1: T-90103 pauses at the approval, and the two writes happen only after the resume. 2: on all 70 tasks, the graph proposes the same as the plain loop. 3: LangGraph runs an interrupted node again from its start, so a write before `interrupt()` happens twice, unless it has an operation ID. |
| [`mcp-example/`](mcp-example) | [Integration boundaries](https://learning.nextia-ai.com/courses/agents/m05/integration-boundaries/) | A small MCP server that offers the project's read-only `get_order`, and a client that lists the tool and calls it four times. Tool hints are not checks: the checks stay in the server's code and in your host. |

Both examples use the recorded model decisions and a copy of the practice database. You need no account, no key and no network after the install. Nothing changes in your own project.

## Where they find the project

Both examples import the course project, `resolution-workflow`. They look for it in this order:

1. The folder in the environment variable `RESOLUTION_WORKFLOW`, if you set it.
2. A folder `resolution-workflow` next to the example folder. Use this when you copy an example next to your own project.
3. A snapshot in this repository: `../../snapshots/end-of-m04` for `langgraph/`, `../../snapshots/end-of-m05` for `mcp-example/`. So both run as they are, inside your clone of this repository.

## Set up and run

You need Python 3.12 and an internet connection for the install. The steps use `mcp-example`. For `langgraph`, use that folder, the name `.venv-lg`, and the script `graph.py`.

On macOS and Linux:

```sh
cd nextia-learning-labs/C10/optional/mcp-example
python3.12 -m venv .venv-mcp
source .venv-mcp/bin/activate
python -m pip install -r requirements.txt
python client.py
```

On Windows, in PowerShell:

```powershell
cd nextia-learning-labs\C10\optional\mcp-example
py -3.12 -m venv .venv-mcp
.venv-mcp\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python client.py
```

When you are done, type `deactivate`. To remove an example's environment, delete its `.venv-mcp` or `.venv-lg` folder.

## Pinned versions

| Example | Packages (`requirements.txt`) | In a fresh environment |
|---|---|---|
| `langgraph/` | `langgraph==1.2.14`, `langgraph-checkpoint-sqlite==3.1.1`, `openai==3.27.0`, `pydantic==2.14.0` | 43 packages |
| `mcp-example/` | `mcp==2.3.0`, `pydantic==2.14.0` | 28 packages |

Agent frameworks and the MCP SDK change fast. With other versions, the code may not run. For example, in `mcp` 2.x the server class is `MCPServer`; older tutorials use `FastMCP`.

## What you see

`langgraph/graph.py` prints this and writes the summary to `result.json`:

```text
1. Paused at: ('approve',) | interrupt value keys: ['approval_request', 'required_role']
   changes before approval: []
   after resume: done [('reship_item', 'done'), ('create_return_label', 'done')] | changes: [('label', 'LK-640436', 'PLANTER'), ('reship', 'LK-640436', 'PLANTER')]
2. Same proposal as the plain loop: 70 of 70; different: []
3. Resume re-runs the node: {'new ID per call (not idempotent)': {'node_runs': 2, 'refunds': 2}, 'operation ID from the ticket and action': {'node_runs': 2, 'refunds': 1}}
```

Part 2 runs the project's plain loop and the graph on the same recorded decisions. So it checks that the graph takes the same steps, not that it decides better.

`mcp-example/client.py` prints the tool, its schema and its hints, then the four calls. The lesson [Integration boundaries](https://learning.nextia-ai.com/courses/agents/m05/integration-boundaries/) shows the full output and explains each line.

## Tested

Tested with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each example, from a fresh copy of this folder: both print the output above. The Windows commands were not run. Code MIT.
