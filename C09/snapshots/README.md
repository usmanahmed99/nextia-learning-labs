# Snapshots: policy-assistant at the start and at the end of each module

Each folder here is the `policy-assistant` project of [RAG: Building AI That Uses Your Data](https://learning.nextia-ai.com/courses/rag/). `start` is the project that you download in the lesson *Corpus and questions*. The others are the project after the last lesson of one module. If your project is broken or missing, copy the snapshot of the module that you finished last, and continue with the next lesson.

| Snapshot | Use it to start | What it has (new) | Tests |
|---|---|---|---|
| [`start`](start) | Module 1, lesson 2 | The policy collection (`corpus/`), the 67 questions, `python -m policy_assistant inventory` and `questions`. | 4 |
| [`end-of-m01`](end-of-m01) | Module 2 | Keyword search with SQLite FTS5 and BM25 over the sections of the Markdown documents (`lexical.py`), hit@5 (`evaluate.py`), `search` and `eval`. | 11 |
| [`end-of-m02`](end-of-m02) | Module 3 | Parsing Markdown, HTML and PDF (`parse.py`), three chunkers (`chunk.py`), stable chunk IDs and metadata (`metadata.py`), the index file (`store.py`), `parse`, `ingest`, `chunks`. | 31 |
| [`end-of-m03`](end-of-m03) | Module 4 | Embeddings (`embed.py`), vector, hybrid and reranked search (`dense.py`, `hybrid.py`, `rerank.py`, `search.py`), date and access filters (`filters.py`), query rewriting (`rewrite.py`), the provider adapter and settings, recorded rewrites and embed-small vectors. | 48 |
| [`end-of-m04`](end-of-m04) | Module 5 | The context (`context.py`), answers with claims and passage IDs (`answer.py`), citation checks (`cite.py`), `ask` (`assistant.py`), recorded answers. | 74 |
| [`end-of-m05`](end-of-m05) | Module 6 | Recall@k, precision@k, MRR and the answer checks (`evaluate.py`), `eval --answers`. | 77 |
| [`end-of-m06`](end-of-m06) | The final assignment | Incremental ingestion and deletions (`store.py`), access checks on citations, prompt `answer_v2` against instructions hidden in documents, `info`, the full README. The course-end project. | 86 |

Each snapshot has only what the lessons' guided practice makes. It does not have the answers to the "Your turn" tasks.

## What a snapshot does not have

- `.env`. Make it from `.env.example` only if you want a live model.
- The virtual environment `.venv` and the index `index.sqlite`. They are made again when you set up and run `python -m policy_assistant ingest`.
- The local models. From `end-of-m03`, the first run downloads two models (about 1 GB in all) into the Hugging Face cache, once.

## Use a snapshot

The steps use `end-of-m03` as an example. Use the name of your snapshot.

1. Get the files. If you have Git, clone this repository once, in `~/projects`:

   ```sh
   cd ~/projects
   git clone https://github.com/usmanahmed99/nextia-learning-labs.git
   ```

   If you already have the clone, get the newest files with `git -C nextia-learning-labs pull`. Without Git, download [the ZIP file of this repository](https://github.com/usmanahmed99/nextia-learning-labs/archive/refs/heads/main.zip), and unzip it in `~/projects`. Its folder is `nextia-learning-labs-main`.
2. Keep your own project. If `~/projects/policy-assistant` exists, rename it:

   ```sh
   mv policy-assistant policy-assistant-old     # Windows: Rename-Item policy-assistant policy-assistant-old
   ```

3. Copy the snapshot into a new `policy-assistant` folder:

   ```sh
   cp -R nextia-learning-labs/C09/snapshots/end-of-m03 policy-assistant
   ```

   On Windows, in PowerShell: `Copy-Item -Recurse nextia-learning-labs\C09\snapshots\end-of-m03 policy-assistant`.
4. Make the virtual environment, run the tests and the first commands:

   ```sh
   cd policy-assistant
   python3 -m venv .venv
   source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   python -m pytest
   python -m policy_assistant ingest
   ```

   `end-of-m03` gives `48 passed`. On Linux, from `end-of-m03`, install the CPU-only PyTorch before the requirements: `python -m pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu`.

## Tested

Tested on 2026-10-09 with Python 3.12 on macOS (Apple silicon), in a new virtual environment for each snapshot and an empty model cache: every snapshot's tests pass, and the stage's commands run with the mock provider. From `end-of-m03`, the virtual environment takes about 0.9 GB and the two models about 0.94 GB; the first test run, with the downloads, took about 36 s. Windows and Linux are not tested.
