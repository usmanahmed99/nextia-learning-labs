# Dataset card: 14 CFR Parts 250 and 254 at every version date, eCFR snapshot of 2026-10-09

Used by: the case study *Answer from versioned regulations* (Nextia Learning, course *RAG: Building AI That Uses Your Data*), project `regulations-assistant`.

| Field | Value |
|---|---|
| Source | The Electronic Code of Federal Regulations (eCFR), versioner API v1: `https://www.ecfr.gov/api/versioner/v1/` (`titles.json`, `versions/title-14.json?part=N`, `full/DATE/title-14.xml?part=N`). Every URL is in `regulations/sources.csv`. |
| Publisher / creator | US Department of Transportation (the rules); Office of the Federal Register and Government Publishing Office (the eCFR) |
| Licence | Public domain: a work of the US government (17 U.S.C. § 105). No attribution is required. |
| Attribution text | We write anyway: "Source: eCFR (ecfr.gov), 14 CFR Parts 250 and 254, fetched 2026-10-09. US government work, public domain. The eCFR is not an official legal edition of the CFR." |
| Version or access date | Fetched once, 2026-10-09, 07:07:49–07:08:22 UTC. The eCFR was up to date to 2026-10-07. Its point-in-time history starts on 2017-01-01. |
| File used | `regulations/`: 13 XML files (Part 250 on 7 dates, Part 254 on 6), 2 versions lists, `titles.json`, `sources.csv`; kept in the project: yes |
| SHA-256 | One per file in `regulations/SHA256SUMS` (SHA-256 of that file: a17f8d610dac4243bb70c4078401c7ce7e08db58e00972b63c6f933e90bf4b20) |
| Size | 16 files, 332 KB; 18 sections, 44 section versions, 16,499 words over all versions; 134 chunks |

## What one row means

One XML file is one part of the regulation **as it was on one date**: `title-14_part-250_2021-04-13.xml` is Part 250 on 13 April 2021. The project compares the files in date order: when a section's text changes, a new **version** of that section starts on that date, and the old one ends the day before. A version is one section (for example § 250.5, *Amount of denied boarding compensation*) with its text and its dates in force. There is no target: the case study asks dated questions about the versions.

The two parts: **Part 250, Oversales** (12 sections: definitions, who must ask for volunteers, boarding priority, how much compensation a passenger denied boarding involuntarily gets, when it is paid, the written notice, reports, signs) and **Part 254, Domestic baggage liability** (6 sections: the minimum limit of an airline's liability for lost, damaged or delayed baggage on domestic flights with large aircraft, and the notice).

## Why this dataset

It has real, dated changes in a small space: the compensation limits of § 250.5 ($675 / $1,350, then $775 / $1,550 from 2021-04-13, then $1,075 / $2,150 from 2025-01-22) and the baggage minimum of § 254.4 ($3,500, $3,800, $4,700). It has amendments that were **published three months before they came into force** (2021-01-13 and 2024-10-24), a **real error corrected** in 2021 (§ 250.5(b)(3) said $1,350 for about four months), and **rules that did not exist yet** (§ 250.7, § 250.2b(d)). Compared with Canada's Air Passenger Protection Regulations on the Justice Laws Website (only two of four versions as OGL XML; the others as HTML under other terms). See the research notes of the case study.

## Changes we made

- None to the files: they are stored exactly as the API returned them (decompressed).
- The project (`regulations_assistant/versions.py`) reads the XML. It keeps paragraphs, flush paragraphs, footnotes, tables (one block each) and the eCFR's notices "Link to an amendment published at …". It keeps the source notes ("[Doc. No. …]") and the approval notes out of the text.
- The first version of every section starts on 2017-01-01 in the project, because the eCFR cannot show an earlier date. Many of these texts were in force earlier; the project says "2017-01-01 or earlier".

## The questions

`questions/questions.jsonl`: 34 questions with a date (`as_of`, the day of the flight or of the question), written by the author by reading the versions; no model wrote or labelled a question. Kinds: dated 15, pending 3 (an amendment published, not yet in force), correction 1, absent 2 (a rule that did not exist yet), stable 6, before 2 (before the snapshot), after 1 (after the eCFR's up-to-date date), not covered 4. Groups ask the same question on several dates, with different reference answers. Each has a reference answer, keys and `must_not` patterns (regular expressions; `must_not` holds the amounts of the other versions), and relevant passages (section, version, paragraph). A script checks that each passage exists and is in force on the question's date, and that each key matches its reference answer. **One change after reading the first recorded answers (2026-10-09):** Q16's `must_not` also catches an answer that starts with "Yes" (one did, and a key had matched its words "did not state"). The set was frozen after this change, before the comparisons. It is one person's reading. Licence of the questions: CC0.

## Limitations and cautions

- **Not legal advice, and not the official text.** The eCFR is not an official legal edition of the CFR; the official edition is the annual CFR on govinfo.gov, and changes are published in the Federal Register. An answer must name the version it used, and a person must check anything that matters.
- **A snapshot that can lag.** It is up to date to 2026-10-07. A change published or in force after that date is not in it. § 250.5(e) and § 254.6 say the amounts are reviewed every two years.
- **History from 2017 only.** The snapshot holds no version before 2017-01-01. For example, the Federal Register shows that the limits were $650 / $1,300 until 2015-08-25 (80 FR 30144); the snapshot cannot show that.
- **Two parts only.** Delays, cancellations, refunds, tarmac delays (Part 259) and international baggage (the Montreal Convention) are not in it.
- **A real error inside a version.** From 2021-04-13 to 2021-08-01, § 250.5(b)(3) says $1,350 and § 250.9 says $1,550 for the same case. The questions follow the text of § 250.5; a reader may weigh it differently.
