# Dataset card: GOV.UK guidance on rights at work, snapshot of 2026-10-09

Used by: the case study *Answer questions from public guidance* (Nextia Learning, course *RAG: Building AI That Uses Your Data*), project `guidance-assistant`.

| Field | Value |
|---|---|
| Source | GOV.UK guides and answer pages, read through the GOV.UK Content API: `https://www.gov.uk/api/content/<path>` (one request per guide; paths in `scripts/paths.txt`) |
| Publisher / creator | GOV.UK (Government Digital Service and the government departments that own the pages). Crown copyright. |
| Licence | Open Government Licence v3.0: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ |
| Attribution text | Contains public sector information licensed under the Open Government Licence v3.0. |
| Version or access date | Fetched once, 2026-10-09, 06:21–06:22 UTC (each page's time is in `sources.csv`) |
| File used | `guidance/pages.jsonl` (one line per page, with the body HTML), `guidance/sources.csv` (the same without bodies), kept in the project: yes (the licence allows redistribution) |
| SHA-256 | `pages.jsonl` b48f97342a685b33d517184032f37c4c4c935d6d65af0ee9172a86488d2584bd; `sources.csv` 499806c88713f99a6b19020e12bc9fd9e42fdc28e690aac661b80c5c587081c2 (`guidance/SHA256SUMS`) |
| Size | 137 pages from 38 guides, about 36,000 words; 397 KB |

## What one row means

One line of `pages.jsonl` is one GOV.UK page: a part of a guide (for example *Statutory Sick Pay (SSP): Eligibility*, `https://www.gov.uk/statutory-sick-pay/eligibility`) or a one-page answer (for example *Payslips: employee rights*). It has the page's address, titles, GOV.UK's `public_updated_at` (the last major change) and `updated_at` (the last change of any size), the time we fetched it, the SHA-256 of the API response it came from, and the body as HTML. There is no target: the case study asks questions about the pages.

The topic is rights at work in England, Scotland and Wales: holidays and sick pay, maternity, paternity, adoption, shared parental, neonatal and bereavement leave, time off for dependants and carers, redundancy, dismissal and notice, grievances and disciplinaries, lay-offs, insolvency, rest breaks and working hours, flexible working, contracts, Sunday working, the minimum wage and payslips.

## Why this dataset

It is real public guidance with a clear, permissive licence and an official API, and it has what a guidance assistant must handle: answers that depend on a condition (length of service, age, employment status), rules with dates (6 April 2025, 6 April 2026, 25 July 2026), tables of old and current rates on the same page, and questions that it does not answer (Northern Ireland, an employer's own scheme, personal advice). Compared with Canada.ca pages (non-commercial terms only) and GOV.UK consumer-rights pages (too few guidance pages). See the course's research notes.

## Changes we made

- None to the text. The body HTML is stored exactly as the API returned it.
- The project's parser (`guidance_assistant/parse.py`) reads the HTML and removes the tags and the 9 lines "This guide (or page) is also available in Welsh (Cymraeg)." It keeps the words of links and abbreviations, and keeps each table as one block.
- We chose 38 of 47 candidate pages from four GOV.UK browse sections (list and reasons in the research notes).

## The questions

`questions/questions.jsonl`: 44 questions written by the author by reading the pages (no model wrote or labelled a question): fact 12, condition 14, table 3, dated 5, calculation 2, not covered 8. Each has a reference answer, keys and `must_not` patterns (regular expressions for the automatic check), and its relevant passages (page and section) with their chunk IDs. A script checks that every passage exists and that every key matches its reference answer. **Two changes after reading the first recorded answers (2026-10-09):** the key of Q34 also accepts "not met" (a right answer said "the birth-date condition is not met"); the `must_not` of Q41 no longer matches "whether you should accept" (an abstention was scored as advice). The question set was frozen after these changes, before the comparisons. It is one person's reading. Licence of the questions: CC0.

## Limitations and cautions

- **A snapshot.** GOV.UK changes these pages, at least every April when the rates change. An answer is true of the pages on 2026-10-09, not of today. Every answer shows the fetch date; check the live page.
- **The dates on GOV.UK pages can mislead.** `public_updated_at` is before 2020 for 26 of the 38 guides, although their rates were updated in 2026. `updated_at` is more useful; neither says which sentence changed.
- **England, Scotland and Wales only.** Northern Ireland has different rules (nidirect). The pages often say so without giving the rule.
- **Not legal advice.** GOV.UK says: "We do not publish advice on GOV.UK. You should get professional or specialist advice before doing anything on the basis of the content." Employment law depends on facts that a question rarely gives (employment status, contract terms, dates).
- **Not complete.** 137 pages of one topic. Many questions about work (tax, benefits, tribunals, discrimination, monitoring) need pages that are not in the snapshot.
- **No endorsement.** Use of this guidance does not mean that GOV.UK or any government department endorses this project. Do not present an assistant built on it as an official service.
