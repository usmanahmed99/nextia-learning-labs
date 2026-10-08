# Dataset card: bilingual government answers

Used by: `starter.zip` and `finished.zip` in this folder. The test material of the case study *Choose a model for bilingual government answers* (Nextia Learning, Module 6 of this course).

## What it contains

| File | What it is | Source |
|---|---|---|
| `data/pages/health-coverage.en.md`, `.fr.md` | The text of *How publicly funded health care coverage works* / *Comment fonctionne la couverture de soins de santé financés par des fonds publics* (Health Canada) | Official page, unchanged text |
| `data/pages/water-devices.en.md`, `.fr.md` | The text of *Questions And Answers On Drinking Water Treatment Devices* / *Questions et réponses sur les dispositifs de traitement de l'eau de consommation* (Health Canada) | Official page, unchanged text |
| `data/questions.csv` | 24 questions: 12 in English and the same 12 in French, with a key answer for each | Written for this case study, from the pages |
| `runs/*.jsonl` | The answers of four models to the 24 questions, recorded on 2026-10-08 | Model outputs |

## Sources and licence

| Page | English | French | Date modified (on the page) | Open Government Portal record |
|---|---|---|---|---|
| Health care coverage | [canada.ca/en/…/canada-health-act-frequently-asked-questions.html](https://www.canada.ca/en/health-canada/services/health-care-system/canada-health-care-system-medicare/canada-health-act-frequently-asked-questions.html) | [canada.ca/fr/…/loi-canadienne-sante-foire-questions.html](https://www.canada.ca/fr/sante-canada/services/systeme-soins-sante/systeme-sante-canadien-assurance-sante/loi-canadienne-sante-foire-questions.html) | 2025-07-16 | [8ded4ddf-f3c0-4aa5-ad8a-08a88ef84db6](https://open.canada.ca/data/en/dataset/8ded4ddf-f3c0-4aa5-ad8a-08a88ef84db6) ("Canada Health Act - Frequently Asked Questions") |
| Drinking water treatment devices | [canada.ca/en/…/questions-answers-drinking-water-treatment-devices.html](https://www.canada.ca/en/health-canada/services/environmental-workplace-health/water-quality/questions-answers-drinking-water-treatment-devices.html) | [canada.ca/fr/…/questions-reponses-dispositifs-traitement-eau-consommation.html](https://www.canada.ca/fr/sante-canada/services/sante-environnement-milieu-travail/qualite-eau/questions-reponses-dispositifs-traitement-eau-consommation.html) | 2023-05-30 | [92ef0a7f-d8d9-4157-8267-b54dd4359c93](https://open.canada.ca/data/en/dataset/92ef0a7f-d8d9-4157-8267-b54dd4359c93) |

Retrieved on 2026-10-08.

**Licence: [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada) (version 2.0).** How we checked it, for these exact pages:

1. The general [Canada.ca terms](https://www.canada.ca/en/transparency/terms.html) allow non-commercial reproduction "unless otherwise specified", and ask for written permission for commercial redistribution. That alone is not an open licence.
2. Each of the two pages has its own record on the Open Government Portal (open.canada.ca), published by Health Canada. Both records list the English and French page as their resources, with the licence "Open Government Licence - Canada" (`ca-ogl-lgo`). We read the records through the portal's API on 2026-10-08.
3. So these two pages are "otherwise specified": they are published under the OGL – Canada, which allows copying, adapting and redistributing, also commercially, with attribution.

A page without such a record is under the general Canada.ca terms. Check every new page the same way. This is not legal advice.

**Attribution.** Contains information licensed under the Open Government Licence – Canada. Source: Health Canada, the four pages above, retrieved 2026-10-08.

**What the licence does not give.** It does not allow the use of the Government of Canada's names, crests, logos or official symbols, and it does not allow a use that suggests official status or endorsement. An assistant built from these pages must not look like a government service.

## How the material was made

- **Pages.** `fetch_pages.py` (in the case study's source folder) downloaded each page and kept its `<main>` text. Headings became `##`/`###` and list items `- `. The "Page details" block was removed. The words are unchanged, including the original's typing errors in French ("Ca nada", "sytèmes").
- **Questions.** Written for this case study by the course author, in English and in French, from the pages. The routine questions follow the pages' own questions in a person's words. The French questions are not word-for-word translations of the English ones; they ask the same thing. The key answers summarise the page text in English.
- **Kinds.** Per language: 6 routine, 2 difficult (two parts, or a trap in the wording), 2 ambiguous (the answer depends on information that the question does not give), 2 unanswerable (the page does not say; a model may "know" an answer from elsewhere).

## Columns of `questions.csv`

| Column | Meaning |
|---|---|
| `id` | Kind letter and number, then the language: `R1-en`, `R1-fr` (R routine, D difficult, A ambiguous, U unanswerable) |
| `pair` | The same question in the other language has the same pair |
| `language` | `en` or `fr` |
| `kind` | `routine`, `difficult`, `ambiguous`, `unanswerable` |
| `page` | `health-coverage` or `water-devices`; the model gets this page in the question's language |
| `answerable` | `true` if the page answers the question |
| `source_section` | The page section that answers it |
| `question` | The question, as a person would write it |
| `must_include` | Key phrases for the automatic check: groups separated by `;`, alternatives by `\|` |
| `must_not_include` | Phrases that signal an invented fact (for example a number that is not on the page) |
| `key_answer` | What a complete, correct answer says, from the page |

## Checks

- SHA-256 of the files, as recorded on 2026-10-08:
  - `health-coverage.en.md` 148abb58d27040e7ec516703dd12f47773dcc9bbd35c8aa9ae751fc8a863c54c
  - `health-coverage.fr.md` 6ad642f64d49aef5f3b6be6598fc0d8709ef1c0b92ce4b23e3dbe1516d51691a
  - `water-devices.en.md` 346e4b42ca4b27b3d79f769822234e4d4fa84caebf7a6ad5f59886efcc2dbc22
  - `water-devices.fr.md` 1026f4b56a27d67616cbd16094ec99b1c77dc06b1a9c3e8db9ca334b5a7e45b0
  - `questions.csv` 05571fa86fc21bc3078aff484b2309d7b718979de47808ef876f1147d7ae7149
- Every key answer was checked against the page text by the author. Every quote that a model gives is checked against the page by `scripts/check.py`.

## Known gaps and biases

- **Small.** 24 questions from 2 pages. It shows large differences between models, not small ones.
- **Two topics only**, both from Health Canada. Questions about taxes, immigration or benefits may behave differently.
- **Written questions.** Real questions are shorter, have spelling errors, and mix topics. These are cleaner.
- **The pages age.** The water page (2023) names "Industry Canada", now Innovation, Science and Economic Development Canada. The answer key follows the page; a real service must also review its sources.
- **One scorer.** The answers were scored by one person who reads both languages. A second scorer would measure agreement.
