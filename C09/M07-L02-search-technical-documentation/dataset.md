# Dataset card: SQLite 3.53.4 documentation (195 pages) and a labelled question set

Used by: the case study [Search technical documentation](https://learning.nextia-ai.com/courses/rag/m07/search-technical-documentation/), `search-technical-documentation.ipynb`

| Field | Value |
|---|---|
| Source | The official documentation archive of SQLite 3.53.4, https://sqlite.org/2026/sqlite-doc-3530400.zip (linked from https://sqlite.org/download.html) |
| Publisher / creator | The SQLite developers (Hwaci) |
| Licence | **Public domain**: "All of the code and documentation in SQLite has been dedicated to the public domain by the authors." (https://sqlite.org/copyright.html). The question set and labels were written for this course and are also dedicated to the public domain (CC0 1.0). |
| Attribution text | Not required. We write: "SQLite 3.53.4 documentation, https://sqlite.org/ (public domain)." |
| Version or access date | Release 3.53.4; downloaded 2026-10-09 |
| File used | `data/sqlite-doc-3530400-pages.zip`, kept: yes (public domain). Original archive SHA-256 `a1d0f5de57485d062796ed7e67daff0758b50d00001a0f233a2c15aaf40bbdc8` (11,820,412 bytes) |
| SHA-256 | See `data/SHA256SUMS` (pages zip `22ddd7e72f28b2f629f941f6e3f80763be1b9d9002f58318a9aac7b2e5793aa8`) |
| Size | 195 HTML pages (3.06 MB zipped) → 2,231 sections → 4,300 chunks, 597,305 words; 53 questions with 122 relevant passages |

## What one row means

One **chunk** is a part of one section of one documentation page, at most 200 words, with its page (`doc_id`), section heading, anchor and URL (for example `https://sqlite.org/pragma.html#pragma_busy_timeout`). One **question** has a kind (identifier, paraphrase, how-to, unanswerable), a reference answer and its relevant passages (page + section anchor, and in a long section an `evidence` text).

## Why this dataset

Exact names (result codes, pragmas, C functions, CLI options, compile options) and plain-language questions both matter, as in real developer support. Compared with the pytest 9.1.1 docs (MIT; Sphinx sources need a build) and the Kubernetes docs (CC BY 4.0; 1,721 pages with no tagged versions), SQLite is public domain, versioned, the right size after a documented selection, and parseable with provenance using only Python's standard library. Full comparison: `reference/c09/m07/l02/DATASET-RESEARCH.md` in the course repository.

## Changes we made

- Kept the 224 top-level pages minus 29 that are not technical documentation (indexes, news, release history, organisation and legal pages) and left out the sub-folders (c3ref repeats capi3ref; release logs; syntax diagrams; session C API). The kept pages are unchanged.
- Chunks: navigation marked `<div class=nosearch>`, scripts and SVG diagrams removed; one chunk per section, split between blocks at 200 words; tables longer than 200 words split between rows with the header row repeated.
- Vectors: e5 (`intfloat/multilingual-e5-small` @ `614241f622f53c4eeff9890bdc4f31cfecc418b3`, float16) and the recorded hosted `embed-small` (text-embedding-3-small on Azure, 2026-10-09, float16).
- Recorded answers: `chat-small` (gpt-6-luna on Azure, 2026-10-09) for 9 questions.

## Limitations and cautions

- The labels are one person's reading, with pooling from the six compared methods (top 5 each) and a second reading; a relevant section that no method found is missing for all.
- 48 scored questions: a difference of one question is 0.021 of hit@5.
- The documentation contains near-duplicates (`fileformat.html` = `fileformat2.html`) and pages about old versions (`c_interface.html` is the SQLite **Version 2** C interface). Answers must cite the page and version.
- This is a snapshot of 3.53.4. SQLite's documentation changes with each release; do not present answers as SQLite's official support.
