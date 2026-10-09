# Dataset card: Larkfield's policy collection and question set

Used by: the course *RAG: Building AI That Uses Your Data*, Modules 1 to 6 and the final assignment; the project `policy-assistant` (`../snapshots/`).

| Field | Value |
|---|---|
| Source | Written for this course by Nextia. Not taken from any real company. Larkfield is a fictional online shop for home and garden products in Canada. |
| Publisher / creator | Nextia. The facts of every document were specified by the course lead; the prose was drafted by a language model from those specifications and reviewed by the lead (see "How it was made"). |
| Licence | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) |
| Attribution text | None needed. "Synthetic Larkfield policy collection, Nextia Learning" is welcome. |
| Version or access date | 1.0, built 2026-10-09. The course's "today" is 2026-10-09. |
| File used | All files below, kept here: yes |
| SHA-256 | Every file: `SHA256SUMS`. `inventory.csv` d58fd45c05d6e67650ba8ae1c29377e15a71f24b4892dc1e787f5e362f5e52a1; `../questions/questions.jsonl` 5d8fa684cd9b4e44c3f5254167a2380ac649b588ca8c06eaf5433d5b3479158b |
| Size | 36 documents, 6,520 words (as parsed); 67 questions. 260 KB in all. |

## What the files are

| Path | What it is |
|---|---|
| `documents/` | The collection as the assistant receives it: 36 documents, of which 32 are Markdown (front matter + text), 2 are HTML pages (`returns-policy.v4.html`, `delivery-policy.html`) and 2 are PDF files (`warranty-policy.pdf`, two pages; `product-care-pw2200.pdf`). |
| `formats/` | Those 4 documents in all three formats (`.md`, `.html`, `.pdf`), for comparing parsers. The Markdown is the source; HTML and PDF were rendered from it by a script. |
| `inventory.csv` | One row per document: `file, doc_id, title, version, effective_from, effective_to, owner, access, language, doc_type, format`. |
| `difficulties.md` | The difficulties put into the collection on purpose, and the questions that test them. |
| `../questions/questions.jsonl` | Grace's 67 questions (one JSON object per line). |

## What one row means

**A document** has front matter (in HTML: `<meta>` tags; in PDF: the Keywords field): `doc_id`, `title`, `version`, `effective_from`, `effective_to` (optional), `owner`, `access` (`public` or `staff`), `language` (`en` or `fr`), `doc_type` (`policy`, `procedure`, `guide`, `help`, `notice`, `supplier`). Two documents share a `doc_id`: the returns policy, versions 3 and 4.

Contents: customer policies (returns, refunds and payments, delivery, large items, damaged items, warranty, privacy, Rewards, gift cards, account, order changes, installation, trade accounts, promotions, recycling, live plants), a governance document with the precedence rules, help articles (an English FAQ, a Quebec FAQ in French, contact and hours), notices (an expired holiday extension, a kettle safety notice), product guides (two near-identical pressure washers, a BBQ, a hedge trimmer, garden furniture), one supplier product sheet, and six staff-only procedures. 6 documents are staff-only; 2 are in French.

**A question** has: `id`, `question`, `language`, `kind` (`answerable` 18, `unanswerable` 8, `version` 8, `table` 8, `exact-code` 11, `contradiction` 4, `staff-only` 7, `injection-bait` 3), `as_of` (the date that decides which version applies: the delivery date for returns, otherwise the day of the question; 2026-10-09 when the question has no date), `public_ok` (may a customer-facing assistant give this answer; false for 8), `abstain` (true for the 8 the documents cannot answer), `reference_answer`, `keys` and `must_not` (regular expressions for an automatic check of an answer), `relevant` (the passages that hold the answer: document, version, section heading, access), `relevant_chunks` (the IDs of the structure-aware chunks that cover those passages, from the project's code), `wrong_version` (passages of a version not in force on `as_of` that state a different rule), `tags`, `notes`. 9 questions are in French.

## Why this dataset

The course teaches retrieval-augmented generation with its real difficulties: versions and dates, contradictions, tables, exact codes, access labels, another language, an instruction hidden in a document, and questions with no answer. A public document collection would have some of them, by chance, in unknown amounts, and no reference answers. A synthetic collection has every difficulty on purpose, in known places (`difficulties.md`), so every retrieval score and every answer in the lessons can be checked. It is small enough (6,520 words) for a learner to read in full. It continues the Larkfield story of the earlier courses: the same five help-desk teams, about 45 tickets a day, and Grace's support policy of the LLM applications course (30-day returns, damaged items reported within 14 days, delivery in 3 to 5 business days, refunds in 5 to 10 business days, a 2-year warranty on garden tools and furniture).

## How it was made

1. The course lead wrote a specification for every document (`reference/c09/corpus/specs.py` in the site repository): the exact section headings and every fact, number, price, period, date, code and rule.
2. A language model (gpt-6.1-sol, Azure deployment `chat-strong`, 2026-10-09) turned each specification into prose, with the instruction to add no fact. 36 calls, US$0.135, plus one trial call, US$0.015.
3. A script checked every document against its specification (front matter, headings in order, every number and code in the text present in the specification, no specified code missing): 0 problems.
4. The lead read every document. Three hand edits (below). The front matter was never written by a model.
5. A build script rendered 4 documents as HTML and PDF (reportlab, fixed dates and IDs) and wrote the inventory and the checksums. Built twice: identical byte for byte.
6. The lead wrote the 67 questions, reference answers, keys and relevant passages by reading the documents. A script checked each one (the passages exist and are in force on the question's date; public questions have a public passage; the keys match the reference answer). No model wrote or labelled a question. Four exact-code questions (Q64–Q67) were added after the first retrieval runs showed that codes inside full sentences did not separate keyword and vector search; eight keys were loosened after reading the first recorded answers (for example "3 years" also matching "3-year").

## Changes we made (hand edits after the model's drafts)

- `refund-approval-procedure.md`, *Rules*: "... except damaged items under 50 dollars **and warranty claims under the warranty claims procedure**" (an unintended contradiction with the warranty procedure).
- `large-item-delivery.md`, *Delivery options and fees*: added "Free standard shipping for Larkfield Rewards Gold members does not cover large item delivery fees." (an unintended gap).
- `supplier-aquaflow-hose-reels.md`, *Support*: the two last paragraphs were written by hand, including the hidden instruction (see `difficulties.md`, section 8).

## Limitations and cautions

- Everything is made up: the company, its policies, products, codes, prices, people and email addresses (`.example` domains). The French documents mention Quebec's consumer protection law only in general terms; they are not legal information.
- The documents are short and clean compared with real policies: real collections have longer documents, scanned PDFs, images and many more versions.
- The relevant passages and keys are one person's reading. The automatic answer check (keys) is a net with holes; read the misses.
- A language model drafted the prose: wording can be smoother than real policies, and the PW-2200 and PW-2400 guides are near-identical on purpose.
