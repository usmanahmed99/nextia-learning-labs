# policy-assistant

The project of the course *RAG: Building AI That Uses Your Data* (Nextia Learning). You build Larkfield's policy assistant: a help-desk agent asks a question in plain words, and the assistant answers from Larkfield's own policy documents, with a citation for every claim, or says that the documents do not answer it.

You need no account and no key. Search runs on your computer. Answers come from recorded model responses (the mock provider) unless you choose a live model.

## What is in the folder

| Path | What it is |
|---|---|
| `corpus/documents/` | Larkfield's policy collection: 36 documents (32 Markdown, 2 HTML, 2 PDF). Synthetic: made up for the course, CC0. |
| `corpus/formats/` | Four of the documents in all three formats (Markdown, HTML, PDF), for comparing parsers. |
| `corpus/inventory.csv` | One row per document: its ID, version, dates, owner, access label, language, type and format. |
| `questions/questions.jsonl` | Grace's 67 questions, with reference answers and relevant passages. |
| `policy_assistant/` | The code. It grows module by module. |
| `tests/` | The tests (`pytest`). |

## Set up (once)

You need Python 3.12 or later.

macOS and Linux:

```sh
cd policy-assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd policy-assistant
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## The known-good first run

```sh
python -m pytest
python -m policy_assistant inventory
```

The tests pass, and the last line of the inventory is:

```text
36 documents: 6 staff-only, 2 in French, 4 not Markdown
```

## From Module 3: two local models

From Module 3, `requirements.txt` includes PyTorch and sentence-transformers (about 0.9 GB installed), and the first search with vectors downloads two models into the Hugging Face cache (`~/.cache/huggingface`, about 1 GB in all): `intfloat/multilingual-e5-small` (embeddings, MIT) and `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` (reranking, Apache-2.0). On Linux, install the CPU-only PyTorch first: `python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu`.

## Reset

If something is broken, delete `.venv` (and `index.sqlite` if it exists), and set up again. If your code is broken, copy the snapshot of the last module that you finished from the course's labs repository (`C09/snapshots/`).

## Licence

Code: MIT (see `LICENSE`). Documents, questions and recordings: CC0.
