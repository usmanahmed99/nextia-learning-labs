# Dataset card: CPSC recall notices, home and garden, April to June 2026

Used by: the case study "Extract product recalls into structured data" (C08-M07-L01), project `recall-extractor`

| Field | Value |
|---|---|
| Source | US Consumer Product Safety Commission (CPSC) Recalls API: https://www.saferproducts.gov/RestWebServices/Recall (documentation: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information) |
| Publisher / creator | US Consumer Product Safety Commission |
| Licence | US government work, not under copyright in the US. CPSC's Privacy and Security Notice (https://www.cpsc.gov/id/node/16598): "You may freely copy and distribute recall notices, including photographs of recalled items, without permission." Web page text "may not be used in a way that states or implies CPSC endorsement"; "please credit CPSC". |
| Attribution text | Recall notices: US Consumer Product Safety Commission (cpsc.gov), Recalls API, downloaded 2026-10-08. Selected and laid out by Nextia Learning. Not endorsed by CPSC. |
| Version or access date | Downloaded 2026-10-08: all recalls with a recall date from 2026-01-01 to 2026-10-07 (471 recalls, 1.44 MB, SHA-256 `cd678ee7818469bef99088547c88800e66ecc23b99603ec06b5cfd1c59f8b59b`) |
| File used | `data/notices.json` (41 notices), kept in the project: yes (recall notices may be copied and distributed) |
| SHA-256 | `8deb39097a91aba3c201a188045504342353916f6a743cedb595f7e06f31ffe7` (`data/notices.json`) |
| Size | 41 notices × 21 API fields, 118 KB. Reference: 40 records × 13 fields (`data/reference.json`) |

## What one row means

One recall notice of CPSC: a product that a company recalls, why (the hazard), what a consumer can get (refund, replacement, repair), how many units, where and when it was sold, and whom to contact. `recalls/notices.py` lays each record out as the text that a person reads on cpsc.gov. The target is a structured record of 13 fields; `data/reference.json` holds the hand-checked record of 40 notices.

## Why this dataset

Real safety notices with free text, in the same sections every time, under terms that allow copying. Compared with Health Canada's Recalls and Safety Alerts (Open Government Licence – Canada), whose open file has short labels only (no units, retailers or sale dates), and openFDA enforcement reports (food, drugs and devices, not home-and-garden products). Details: `reference/c08/m07/l01/DATASET-RESEARCH.md` in the course repository.

## Changes we made

- **Window and selection.** Recall dates from 2026-04-01 to 2026-06-30 (160 recalls). The case-study author kept 49 whose product a home-and-garden shop could sell, and drew 40 with `random.Random(7)`. One later notice (26773, 2026-09-17) is added for the end-to-end run.
- **Images removed.** The `Images` field (photo links) is left out.
- **No other change.** Typing errors and errors of the source are kept (below).

## How the reference was made

The case-study author read each of the 40 notices and wrote its record by hand, with the rules of `recalls/prompts/extract.md` (the same rules that the model gets), on 2026-10-08, before any model was run (git history). After the runs, the author reviewed every field where a recorded hosted model disagreed with the reference (3 fields in 3 notices). No reference value changed. Three values stay a matter of reading: 26582 (is "fire" a hazard when the detector fails to alert?), 26537 ("HSN televised shows") and 26485 ("Costco retail stores"). One person checked each notice once: the reference is one careful reading, not an official record.

## Limitations and cautions

- **Not official.** The records are extractions for teaching. Always use the notice on cpsc.gov.
- **An easy sample.** The notices have labelled sections, and many are near copies (9 pool or spa drain covers, 5 dressers, 4 pressure washers). Free-form notices from other sources are harder.
- **Errors in the source.** 26554's title names Arctic Zone coolers, but the rest of the record describes children's pajamas (the reference follows the body). 26444's title says 8.2 million units; its Units line adds up to 8.1 million. 26406 spells the brand BAYOTAK and BATOYAK. 26423's email runs into the next word.
- **US only.** Units sold in Canada or Mexico are left out by rule.
- **Small.** 40 notices: a difference of one or two fields between models is not evidence.
