# Dataset card: arXiv computer-science records, February and March 2024

Used by: the case study *Vector search over an open document collection*, the project `paper-search` (starter.zip, finished.zip)

| Field | Value |
|---|---|
| Source | arXiv's OAI-PMH interface, `https://oaipmh.arxiv.org/oai`, format `arXiv`, set `cs` |
| Publisher / creator | arXiv (Cornell University); each record describes a paper by its authors |
| Licence | The metadata (title, abstract, authors, identifiers, categories) is under **CC0 1.0** (public domain dedication): "You are free to use descriptive metadata about arXiv e-prints under the terms of the Creative Commons Universal (CC0 1.0) Public Domain Declaration." ([arXiv API Terms of Use](https://info.arxiv.org/help/api/tou.html)). The papers themselves (the PDFs) have their own licences and are **not** part of this dataset. |
| Attribution text | "Metadata from arXiv.org (CC0 1.0). Thank you to arXiv for use of its open access interoperability." CC0 does not require credit; arXiv's [API page](https://info.arxiv.org/help/api/index.html) asks for this sentence. This project is not endorsed by arXiv. |
| Version or access date | Harvested on 2026-10-09 and 2026-10-10: the records whose arXiv datestamp (date of the last change to the record) is 1 February to 31 March 2024 (`arxiv-cs-2024-papers.jsonl.gz`), and 1 to 16 April 2024 (`arxiv-cs-2024-04-new.jsonl.gz`). A record that changed after that date has a later datestamp and is not in the files. |
| Files used | `arxiv-cs-2024-papers.jsonl.gz` and `arxiv-cs-2024-04-new.jsonl.gz`, kept in the labs repository (CC0 allows it) |
| SHA-256 | papers `fb138597e9beaf56d6a2176652f6e6303d9c5b8169409e07a236bef607c06006`; April `1b924ae04f2754a4863445e341a56c8068b413d47df9b4dac002ed4108fbd47f` |
| Size | 15,469 records (8.4 MB gzip), and 300 April records (0.2 MB); 12 fields each |

## What one row means

One arXiv record: one paper as it is described on arXiv, with its ID (`2402.05035`), title, abstract, categories (the first one is the primary category), authors, the date of the first version (`created`) and of the newest version (`updated`), and the DOI, journal reference, comments and the paper's own licence URL when they exist. There is no target: the case study searches the abstracts.

## Why this dataset

The case study needs real documents with a clear permissive licence, a few tens of thousands at most, with metadata to filter on and a natural reason to delete a document. arXiv's metadata is CC0, the abstracts are real paragraphs of 10 to 486 words, the primary category is a natural filter with rare and common values (cs.CV 3,344 papers, cs.IR 330, cs.DB 91), and withdrawn papers are a real reason to remove a record. It was compared with US government text (the Federal Register: public domain, but a bot check blocks scripted access to its site, and many notices have no abstract) and Wikipedia (CC BY-SA: share-alike is outside the course's licence rule). See `reference/c20/m06/l02/DATASET-RESEARCH.md` in the course repository.

## Changes we made

- Kept records whose primary (first) category starts with `cs.` and that have a title and an abstract: 15,469 of 18,926 harvested records for February and March; 3,457 had another primary category.
- Collapsed runs of white space (line breaks in titles and abstracts) to one space. No other change to any text. LaTeX stays as it is (1,451 abstracts contain `$`).
- Author names are "forenames keyname", as arXiv gives them.
- The April file is 300 records chosen with a fixed seed (2025) from the 4,803 computer-science records of 1 to 16 April 2024. None of them is in the February-March file.
- Scripts: `harvest.py` (one request every 4 seconds, as arXiv's terms ask) and `parse.py` in `reference/c20/m06/l02/` of the course repository. The same harvest gives the same bytes.

## Limitations and cautions

- **A sample, not arXiv.** Records last changed in February or March 2024. Most papers are from 2024 (14,519); a few older papers are there because their record changed then. Do not draw conclusions about arXiv or a field from it.
- **Abstracts only.** No full text. Search quality on abstracts says little about search on full papers.
- **Real names.** Authors are real people, published by arXiv with their papers. Use the names to show who wrote a paper, never to build profiles of people.
- **Withdrawn papers are still here.** At least two records say in their comments that the paper was withdrawn (`2402.05035`, `2402.02616`). The case study removes one on purpose.
- **One near-duplicate pair.** Two records (`2311.16203`, `2403.05029`) have the same abstract and different titles.
- **English and LaTeX.** Abstracts are English, with LaTeX markup for formulas, which the embedding models read as plain characters.
