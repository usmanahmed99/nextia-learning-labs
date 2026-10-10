# AI System Design and Cost Engineering

Files for the course [AI System Design and Cost Engineering](https://learning.nextia-ai.com/courses/system-design/).

| Folder | What it has |
|---|---|
| [`snapshots/`](snapshots) | The course project, the design pack: `start` (download it in the first lesson) and the pack at the end of each module. MIT. |
| [`data/`](data) | The recorded model calls and the list prices that the pack's `measured.toml` and `prices.toml` come from, with a [dataset card](data/dataset.md). CC0. |
| [`M07-L01-cost-and-capacity-plan/`](M07-L01-cost-and-capacity-plan) | Case study 1, [Cost and capacity plan from real demand data](https://learning.nextia-ai.com/courses/system-design/m07/cost-and-capacity-plan-from-real-demand-data/): a notebook and its solution, and Boston's 311 service requests from residents, counted per hour from January 2022 to July 2025 (PDDL 1.0), with a [dataset card](M07-L01-cost-and-capacity-plan/dataset.md). The notebook runs the course's design pack (the files of `snapshots/end-of-m06`) on the city's demand. Code MIT. |
| [`M07-L02-design-review/`](M07-L02-design-review) | Case study 2, [Design review of an open document-question service](https://learning.nextia-ai.com/courses/system-design/m07/design-review-of-an-open-document-question-service/): the project `open-docs-review` as `starter.zip` (the files you write are missing or are templates) and `finished.zip` (the whole review), and in `data/` the OSHA documents of the US Federal Register (public domain) with a [dataset card](M07-L02-design-review/dataset.md). The project downloads the documents from this repository and checks their SHA-256. Code MIT. |

The case studies use real open data, not Larkfield's, and need an internet connection for their setup steps. They check the SHA-256 of every file that they download.

You need Python 3.12 or newer. The calculator uses only the Python standard library. You need no account, no key and no money. The first case study also needs pandas and matplotlib (Colab and Kaggle have them). The second case study needs tiktoken, to count tokens.
