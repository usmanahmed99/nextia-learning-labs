# AI Security, Privacy and Responsible Design

Files for the course [AI Security, Privacy and Responsible Design](https://learning.nextia-ai.com/courses/ai-security/).

| Folder | What it has |
|---|---|
| [`data/`](data) | The two shops' help-desk data: customers, orders, tickets, attached files, help documents, a small fake website and two made-up secrets, plus the security evaluation set (normal tasks and harmless attacks), with a [dataset card](data/dataset.md). Everything is made up. CC0. |
| [`snapshots/`](snapshots) | The course project `support-assistant`: `start` (download it in Module 1) and the project at the end of each module. Each snapshot has only the code the modules so far teach. Code MIT; data and recordings CC0. |

The attacks are harmless and run only against the practice app on your computer. They try to make the assistant reveal a made-up secret, call a tool it should not, send to a made-up outside address, or read the other shop's made-up records. Never test a system you do not own or have permission to test.

You need no account and no key. The orders, documents, files and websites are all local, and every model decision comes from a recording of a real model. A live model is optional (a free local model through Ollama, or your own key).

## Tested

Tested with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot: every snapshot's tests pass, and the commands of its module run with the recorded model decisions. Windows and Linux are not tested.
