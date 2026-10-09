# policy-assistant

The project of the course *RAG: Building AI That Uses Your Data* (Nextia Learning), as it is at the end of the course. Larkfield's policy assistant: a help-desk agent asks a question in plain words, and the assistant answers from Larkfield's own policy documents, with a citation for every claim, or says that the documents do not answer it. It never decides for the agent; it shows the evidence.

You need no account and no key. Search runs on your computer (SQLite full-text search, a small open embedding model and a small open reranker). Answers come from recorded model responses (the mock provider) unless you choose a live model.

## The pipeline

```text
corpus/documents  ->  parse  ->  chunk  ->  index (SQLite: chunks, BM25, vectors, metadata)
question  ->  filters (date, access)  ->  BM25 + vectors  ->  fusion (RRF)  ->  rerank  ->  top 5
top 5  ->  context (budget, no near-duplicates)  ->  model (claims + passage IDs)  ->  citation checks
```

## Files

| Path | What it does |
|---|---|
| `policy_assistant/documents.py` | The inventory (`corpus/inventory.csv`), Markdown front matter, Module 1's sections |
| `policy_assistant/parse.py` | Markdown, HTML and PDF into the same clean blocks, with section and page |
| `policy_assistant/chunk.py` | Fixed-size, overlapping and structure-aware chunks |
| `policy_assistant/metadata.py` | `Chunk` and its stable ID (SHA-256 of document, version and position) |
| `policy_assistant/lexical.py` | Keyword search: SQLite FTS5 with BM25 |
| `policy_assistant/embed.py` | Embedding models: local (multilingual-e5-small), recorded (embed-small), live |
| `policy_assistant/dense.py` | Vector search with NumPy (cosine similarity, brute force) |
| `policy_assistant/hybrid.py` | Reciprocal rank fusion |
| `policy_assistant/rerank.py` | The cross-encoder reranker |
| `policy_assistant/filters.py` | Version in force on a date; access label for the audience |
| `policy_assistant/search.py` | `Retriever`: bm25, dense, hybrid, rerank, with the filters applied first |
| `policy_assistant/store.py` | The index file; incremental ingestion by content hash; deletions that reach every table |
| `policy_assistant/rewrite.py` | Query rewriting with a model |
| `policy_assistant/context.py` | The token budget, near-duplicates, the passage format |
| `policy_assistant/answer.py` | The answer schema (claims with passage IDs), the request, parsing |
| `policy_assistant/cite.py` | Citation checks in code, and their limits |
| `policy_assistant/assistant.py` | `ask()`: the whole pipeline |
| `policy_assistant/evaluate.py` | hit@k, recall@k, precision@k, MRR; automatic answer checks |
| `policy_assistant/providers.py`, `config.py` | The adapter: the mock (recordings) or a live OpenAI-compatible provider; settings |
| `policy_assistant/prompts/` | `answer_v1.md`, `answer_v2.md` (adds the defence against instructions in documents), `closed_book.md`, `rewrite.md` |
| `corpus/` | 36 documents (32 Markdown, 2 HTML, 2 PDF), `inventory.csv`, four documents in three formats. Synthetic, CC0. |
| `questions/questions.jsonl` | Grace's 67 questions with reference answers and relevant passages |
| `recordings/` | The recorded model responses that the mock replays, and recorded embed-small vectors |
| `tests/` | `pytest` tests |

## Set up

You need Python 3.12 or later and about 2 GB of disk space: about 0.9 GB for the Python packages (PyTorch is most of it) and about 1 GB for the two local models, which are downloaded once, on first use, into the Hugging Face cache (`~/.cache/huggingface`; set `HF_HOME` to put it elsewhere).

| Model | What for | Download | Licence |
|---|---|---|---|
| `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` | embeddings (384 numbers per text; English and French) | about 470 MB | MIT |
| `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, revision `1427fd652930e4ba29e8149678df786c240d8825` | reranking | about 470 MB | Apache-2.0 |

macOS and Linux:

```sh
cd policy-assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Linux, install the CPU-only PyTorch first (`python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu`), or pip downloads the much larger CUDA build.

Windows (PowerShell):

```powershell
cd policy-assistant
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```sh
python -m pytest                                   # the tests (the first run downloads the models)
python -m policy_assistant inventory               # the documents
python -m policy_assistant ingest                  # build index.sqlite (structure-aware chunks, e5 embeddings)
python -m policy_assistant search "Which pump kit fits the PW-2200?" --method bm25
python -m policy_assistant ask Q22                 # a recorded answer, with its citations checked
python -m policy_assistant eval                    # retrieval measures on the 67 questions
python -m policy_assistant eval --answers          # and the recorded answers
python -m policy_assistant audit                   # recorded answers that cite removed or obsolete passages
python -m policy_assistant info                    # how the index was built
```

Every command prints its options with `--help`. Dates are `YYYY-MM-DD`; without `--as-of`, the course's date (2026-10-09) is used, so that your results match the lessons. Use `--as-of today` for real use.

### Recorded answers and live models

The mock replays the answers that were recorded for the course: the 67 questions (by ID, for example `ask Q22`, or the same question text), with chat-small or chat-strong (`--model`) and prompt `answer_v1` (and, for some questions, `answer_v2` and `--audience public`). They were recorded with `--method rerank` (best) and `--method bm25` (weak), top 5, the structure-aware chunker and the e5 model.

- If your search gives exactly the recorded passages, the answer is replayed silently.
- If your passages differ (another method, chunker, `--k`, or a small numeric difference on your computer), the mock still replays the recorded answer of that question, prompt and model, and prints one line: `Note: Recorded with passages …; yours: …`. The citation checks then run against **your** passages, so a recorded citation that your search did not find is reported (`not_in_context`). With `eval --answers`, the answer measures then describe the recorded search, not yours; the command lists those questions.
- A question, prompt or model that was never recorded gives "No recording for this request".

To ask anything else, or to measure answers from your own search, use a live model: copy `.env.example` to `.env` and choose a local model (Ollama, free) or your own key. Never commit `.env`.

| Variable | Meaning |
|---|---|
| `ASSISTANT_PROVIDER` | `mock` (default) or `openai_compatible` |
| `ASSISTANT_MODEL` | `chat-small` (default), `chat-strong`, `gemma3:4b`, or your provider's model name |
| `ASSISTANT_BASE_URL` | for example `http://localhost:11434/v1` (Ollama) or `https://api.openai.com/v1` |
| `ASSISTANT_API_KEY` | your key (never printed) |
| `ASSISTANT_TIMEOUT_S` | seconds before a call gives up (60) |
| `ASSISTANT_TORCH_THREADS` | CPU threads for the local models (default: all) |

## Rebuild and update

`python -m policy_assistant ingest` updates the index. It reads only the documents whose content changed (SHA-256 of the file), and removes the documents whose file is gone, from the chunks, the keyword index and the vectors. Two files with the same document ID and version are refused, and the index stays as it was.

- **A correction** (same version): edit the file and run `ingest` (`1 updated`).
- **A new version**: add a new file with the next version number and its `effective_from`, set `effective_to` on the old version, and run `ingest`. Searches then use the version in force on the question's date.
- **A deletion**: delete the file and run `ingest` (`1 removed`). Update `corpus/inventory.csv` too.

Then run `python -m policy_assistant audit`. It lists the recorded answers that cite a passage that is removed, not in force on the question's date, or staff-only for a public audience. In a real assistant, such answers must leave any answer cache. A process that keeps running (a server) sees the change at its next search: the index's version is checked before the chunks and vectors kept in memory are used.

A different chunker or embedding model needs a new index: `python -m policy_assistant ingest --rebuild --chunker fixed`.

## Handoff record

`python -m policy_assistant info` prints what answers depend on: the index (documents, their fingerprint, chunks, vectors), the chunker, the embedding model and its revision, the reranker and its revision, the prompts (with a short hash of each file), the context budget, the Python and package versions, and the command that rebuilds the index. Measured on 2026-10-09 (macOS, Apple silicon, 2 CPU threads for the local models; medians):

| What | Time | Cost |
|---|---|---|
| Ingest all 36 documents with e5 (parse, chunk, embed 185 chunks) | 4.5 s | free (local) |
| A second `ingest` with nothing changed | under 0.1 s | free |
| Embed the collection with embed-small instead (hosted; 443 texts) | 5.5 s | US$0.0005 |
| Search one question: embed it, BM25, vectors | about 6 ms | free |
| Rerank 20 candidates (the slow step of search) | 322 ms | free |
| Answer one question with chat-small (recorded; median / 95th percentile) | 1.46 / 3.72 s | US$0.00017 |
| Answer one question with chat-strong (recorded) | 2.46 / 4.26 s | US$0.0031 |

At about 45 questions a day, chat-small costs about US$0.008 a day, and chat-strong about US$0.14. Prices change: check your provider's price list.

What invalidates the recorded answers: a change to a document, the chunker, the passage format, a prompt or the e5 revision (the recorded requests contain the passages and the prompt). After such a change, measure answers with a live model.

## Reset

Delete `.venv` and `index.sqlite`, and set up again. The models stay in the Hugging Face cache.

## Tested

2026-10-09, Python 3.12.13, macOS (Apple silicon), in a new virtual environment. Windows and Linux are not tested.

## Licence

Code: MIT (see `LICENSE`). Documents, questions and recordings: CC0.
