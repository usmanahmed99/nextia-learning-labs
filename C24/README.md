# AI Security, Privacy and Responsible Design

Files for the course [AI Security, Privacy and Responsible Design](https://learning.nextia-ai.com/courses/ai-security/).

| Folder | What it has |
|---|---|
| [`data/`](data) | The two shops' help-desk data: customers, orders, tickets, attached files, help documents, a small fake website and two made-up secrets, plus the security evaluation set (normal tasks and harmless attacks), with a [dataset card](data/dataset.md). Everything is made up. CC0. |
| [`snapshots/`](snapshots) | The course project `support-assistant`: `start` (download it in Module 1) and the project at the end of each module. Each snapshot has only the code the modules so far teach. Code MIT; data and recordings CC0. |
| [`M07-L01-find-and-remove-personal-data/`](M07-L01-find-and-remove-personal-data) | Case study 1, [Find and remove personal data before it reaches a model](https://learning.nextia-ai.com/courses/ai-security/m07/find-and-remove-personal-data/): the notebook and its solution, the recorded answers of the model and a [dataset card](M07-L01-find-and-remove-personal-data/dataset.md). The notebook downloads the documents of Gretel's synthetic_pii_finance_multilingual (Apache-2.0) from a fixed version on Hugging Face. Every person and number in them is made up. The dataset has made-up keys, and the model copied some of them into its answers: in this copy they show as placeholders such as `<FAKE-AWS-KEY-1>`, and the notebook puts each one back from the document. Code MIT; recordings CC0. |
| [`M07-L02-threat-model-an-open-source-ai-app/`](M07-L02-threat-model-an-open-source-ai-app) | Case study 2, [Threat-model and test an open-source AI application](https://learning.nextia-ai.com/courses/ai-security/m07/threat-model-an-open-source-ai-app/): `starter.zip` (the review project to start from) and `finished.zip` (a finished review to compare with), with a [dataset card](M07-L02-threat-model-an-open-source-ai-app/dataset.md). The project installs the open-source application llm 0.36 (Apache-2.0) from PyPI and replays recorded model answers. Its documents, pages and keys are made up. Project files MIT. |

The attacks are harmless and run only against the practice app on your computer. They try to make the assistant reveal a made-up secret, call a tool it should not, send to a made-up outside address, or read the other shop's made-up records. Never test a system you do not own or have permission to test.

You need no account and no key. The orders, documents, files and websites are all local, and every model decision comes from a recording of a real model. A live model is optional (a free local model through Ollama, or your own key).

## Tested

Tested with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot: every snapshot's tests pass, and the commands of its module run with the recorded model decisions. Windows and Linux are not tested.

Each case-study folder has its own checks. The notebook of case study 1 checks the SHA-256 of every file that it downloads; it needs an internet connection for its setup cells. Both notebooks of case study 1 ran from a fresh copy with Python 3.12 on macOS, in a new virtual environment (*Restart and run all*): the solution passes every check, and the learner notebook runs with no errors. Case study 2 was run from fresh copies of its two zip files with Python 3.12 on macOS.
