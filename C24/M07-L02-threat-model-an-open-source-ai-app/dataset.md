# Dataset card: llm 0.36 and the Wren & Oak practice set

Used by: C24-M07-L02 (Threat-model and test an open-source AI application), `starter.zip` and `finished.zip`

| Field | Value |
|---|---|
| Source | The application: [llm](https://github.com/simonw/llm) by Simon Willison, release [0.36](https://pypi.org/project/llm/0.36/) (GitHub tag `0.36`, commit `764dc386c58b625f3ad9d203e699715ad208455f`). The practice set: made for this case study by Nextia Learning |
| Publisher / creator | llm: Simon Willison and contributors. Practice set and recordings: Nextia Learning |
| Licence | llm: [Apache-2.0](https://github.com/simonw/llm/blob/main/LICENSE) (installed from PyPI, not redistributed). Project files, practice set and recordings: MIT (`LICENSE` in the zip) |
| Attribution text | "llm by Simon Willison, Apache-2.0, https://github.com/simonw/llm" |
| Version or access date | llm 0.36 (released 2026-09-22); checked and recorded 2026-10-10 |
| File used | `llm-0.36-py3-none-any.whl` from PyPI, through `requirements.txt` with hashes; not kept in `data/` (installed by pip) |
| SHA-256 | wheel `801263d046854d15e3f45ee8da5024c23c313d129f67c7c93961649c531bb050`; sdist `e59ad30875a99be2eea0c880543b1ebfe40eea24ae55d4008eb1e12c77964626`; `recordings/chat-small.jsonl` `036db4d0a8d5c8ef8f290dad38aa768c26c0e74c9aabe7995b75de769fd48620` |
| Size | 5 documents, 1 config file, 14 pages, 15 cases (4 tasks, 10 attacks, 1 sealed new case) and 2 checks of llm itself; 372 recorded model answers (1.3 MB) |

## What one row means

One case in `cases.json` is one request that a buyer types into llm, with the files or URLs it
uses. A task has a correct answer; an attack has a goal (a made-up discount in the reply, a made-up
key in the reply, the budget in a URL, a fetch of an internal address). One recording is one model
call: the exact request that llm sent and the answer of chat-small (`gpt-6-luna-2026-09-22` on
Azure, `reasoning_effort: "none"`), in one of three repeats.

## Why this dataset

The case study reviews a real, maintained open-source assistant, so the "data" is the application
itself plus a small practice set that exercises its documented surfaces: documents added with `-f`,
tools from a `--functions` file, URL fetches, templates and its log. llm won over LightRAG, kotaemon,
private-gpt and paper-qa (see `DATASET-RESEARCH.md` in the course repository): it is small (29
packages), permissive, actively maintained, talks to any OpenAI-compatible URL (so recordings
work), and documents its own prompt-injection risks.

## Changes we made

None to llm. The practice files, pages, cases and the obedient stand-in are new. The recordings
are unedited answers; the provider's response `id` field is removed.

## Limitations and cautions

- The practice set is small and made up: 10 attacks are a smoke test, not a benchmark.
- The recorded answers are one model on one date. Another model, prompt or llm version gives
  other answers; the replay server refuses a request it has not recorded.
- `obedient` is a constructed worst case, not a model: it shows what the code allows.
- The review is of a deployment (llm + the team's tools + settings), not a security audit of llm.
  No security bug of llm was found or claimed.
