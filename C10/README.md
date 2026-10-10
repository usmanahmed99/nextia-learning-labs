# AI Agents and Workflow Orchestration

Files for the course [AI Agents and Workflow Orchestration](https://learning.nextia-ai.com/courses/agents/).

| Folder | What it has |
|---|---|
| [`data/`](data) | Larkfield's support-resolution data: 70 tasks (a ticket, the expected outcome and the changes that are allowed or forbidden), the practice database of orders, payments and boxes, the policy passages and Grace's policy, with a [dataset card](data/dataset.md). Made up for the course. CC0. |
| [`snapshots/`](snapshots) | The course project `resolution-workflow`: `start` (download it in Module 1) and the project at the end of each module. Code MIT; data and recordings CC0. |
| [`optional/`](optional) | Two optional examples: the agent loop in LangGraph (Module 4) and a small MCP server (Module 5). Not needed for the course. Code MIT. |
| [`M07-L01-evaluate-a-customer-service-agent/`](M07-L01-evaluate-a-customer-service-agent) | Case study 1, [Evaluate a customer-service agent on a public benchmark](https://learning.nextia-ai.com/courses/agents/m07/evaluate-a-customer-service-agent/): the notebook and its solution, the recorded conversations on τ³-bench retail and a [dataset card](M07-L01-evaluate-a-customer-service-agent/dataset.md). The notebook downloads the benchmark's files from its GitHub repository. Recordings under τ³-bench's MIT licence (`LICENSE-tau2-bench.txt`). |
| [`M07-L02-test-against-injection-in-tool-results/`](M07-L02-test-against-injection-in-tool-results) | Case study 2, [Test an agent against instructions in tool results](https://learning.nextia-ai.com/courses/agents/m07/test-against-injection-in-tool-results/): the notebook and its solution, the recorded runs on AgentDojo's banking suite and a [dataset card](M07-L02-test-against-injection-in-tool-results/dataset.md). The notebook installs AgentDojo (MIT) from PyPI. |
| [`M07-L03-workflow-or-agent-on-open-data/`](M07-L03-workflow-or-agent-on-open-data) | Case study 3, [Workflow or agent? Automate an open-data process](https://learning.nextia-ai.com/courses/agents/m07/workflow-or-agent-on-open-data/): the notebook and its solution, `designs.py`, a fixed and redacted sample of San Diego's Get It Done requests (public domain, ODC PDDL), the recorded model calls and a [dataset card](M07-L03-workflow-or-agent-on-open-data/dataset.md). Code MIT. |

Every case-study folder has a `SHA256SUMS` file, and its notebook checks every file that it downloads. The case studies need an internet connection for their setup cells.

You need no account and no key. The order, payment and shipping systems are a practice database on your computer, and every write goes only to that file. The model decisions come from recordings of real models; a live model is optional (a free local model through Ollama, or your own key).

## Tested

Tested on 2026-10-09 with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot: every snapshot's tests pass, and the stage's first commands run with the mock provider. Windows and Linux are not tested.

The three case-study notebooks were run from a fresh copy of these folders with Python 3.12 on macOS, in a new virtual environment (*Restart and run all*): every solution notebook passes its checks, and every learner notebook runs with no errors.
