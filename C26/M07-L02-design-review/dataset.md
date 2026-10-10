# Dataset card: OSHA documents in the Federal Register, 2021–2025 (and January–September 2026)

Used by: AI System Design and Cost Engineering, case study *Design review of an open document-question service* (project `open-docs-review`, `python -m corpus get`)

| Field | Value |
|---|---|
| Source | Federal Register API, https://www.federalregister.gov/developers/documentation/api/v1 (documents of the agency `occupational-safety-and-health-administration`; each document's plain text from its `raw_text_url`) |
| Publisher / creator | Office of the Federal Register (National Archives and Records Administration) and the US Government Publishing Office; the documents are written by the Occupational Safety and Health Administration (OSHA), US Department of Labor |
| Licence | Public domain in the United States: works of the US government (17 U.S.C. 105). GovInfo's notice: https://www.govinfo.gov/about/policies (Public Domain & Copyright Notice) |
| Attribution text | "Documents from the Federal Register (federalregister.gov), published by the Office of the Federal Register and the US Government Publishing Office. Public domain." Not required by the licence; we give it anyway. |
| Version or access date | Fixed copies made by the course team: every OSHA document published from 2021-01-01 to 2025-12-31, and the new ones from 2026-01-01 to 2026-09-30. The live API keeps adding documents; these files do not change. |
| File used | `osha-fr-2021-2025.jsonl.gz` (628 documents) and `osha-fr-2026-new.jsonl.gz` (83 documents), kept in `data/`: yes (public domain) |
| SHA-256 | `osha-fr-2021-2025.jsonl.gz`: `81b47f96634ae58085323327008297924914932d8687d4673ec55657465c03bc`; `osha-fr-2026-new.jsonl.gz`: `3ee6af82c1395bf549098772a76ffd1645009984aae5ef4dd3cae633bb1ba411` |
| Size | 628 rows × 10 fields, 5.0 MB compressed (21.1 MB of JSON); 83 rows, 0.2 MB compressed |

## What one row means

One document of the Federal Register in which OSHA is an agency: a rule, a proposed rule or a notice. The fields are the API's `document_number`, `type`, `title`, `publication_date`, `page_length` (as `pages`, printed pages), `start_page`, `end_page`, `html_url` (as `url`), the agencies' slugs, and `text`: the plain-text page exactly as the API's `raw_text_url` returns it (a small HTML page with the text inside `<pre>`; `corpus/load.py` removes the markup). There is no target: the case study sizes the collection.

## Why this dataset

The case study needs a real collection of public documents that one tenant of a document-question service would load: with real sizes (documents, printed pages, text), a real rate of new documents, and a licence that allows a fixed copy. We compared it with GOV.UK guidance (Open Government Licence v3.0); see the authors' research notes. The Federal Register won: public domain, stable document numbers, printed page counts, and publication dates that give the real rate of new documents. GOV.UK guidance is edited in place, so a fixed copy goes out of date without a new document to show it.

## Changes we made

None to the text. We kept the fields above and dropped the API's other fields. Rows are sorted by document number and stored as gzip JSON lines with a fixed time stamp, so the same download gives the same bytes. The case study's code removes the HTML wrapper (8.8% of the characters) before it counts words and tokens.

## Limitations and cautions

- **Not the rules in force.** The Federal Register publishes rules when they are made, proposed, corrected or withdrawn. The rules in force are in the Code of Federal Regulations (eCFR). A proposed rule is not a rule. Never present an answer from these documents as legal advice.
- **Very uneven sizes.** The median document has about 1,270 words; the largest (the 2024 heat proposal) has 259,867. The 10 largest documents hold 49% of all tokens.
- **Names and contact details.** Documents name officials and give their telephone numbers and email addresses (the API hides email addresses as "[email protected]"). Do not collect or republish contact details.
- **Copyrighted parts are possible.** GovInfo's notice says government publications may contain copyrighted material used with permission (for example, quoted standards). Quote short passages with their citation.
- **One agency, five years.** OSHA's documents from 2021 to 2025 include two unusual groups: COVID-19 emergency standards (2021) and many proposed rules in July 2025 (25 that month). Another agency or period has another shape.
