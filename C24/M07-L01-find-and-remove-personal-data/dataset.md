# Dataset card: Gretel synthetic_pii_finance_multilingual (test files: English, French, German)

Used by: the case study *Find and remove personal data before it reaches a model* (AI Security, Privacy and Responsible Design, Module 7), `find-and-remove-personal-data.ipynb`

| Field | Value |
|---|---|
| Source | https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual |
| Publisher / creator | Gretel.ai (A. Watson, Y. Meyer, M. Van Segbroeck, M. Grossman, S. Torbey, P. Mlocek, J. Greco), 2024 |
| Licence | Apache License 2.0 (https://www.apache.org/licenses/LICENSE-2.0), as stated in the dataset card |
| Attribution text | "synthetic_pii_finance_multilingual" by Gretel.ai, https://huggingface.co/datasets/gretelai/synthetic_pii_finance_multilingual, Apache-2.0. A fixed sample was taken; nothing in the documents or labels was changed. |
| Version or access date | Repository commit `7b844d16738527a04264f50214cb426a4cea0897` (2024-06-11), downloaded 2026-10-10 |
| File used | `data/English_test-00000-of-00001.parquet`, `data/France_test-00000-of-00001.parquet`, `data/German_test-00000-of-00001.parquet`; kept in `data/`: no (the notebook downloads them from the pinned commit; the licence would allow a copy) |
| SHA-256 | English `c02b06d3c5b7c375525136d6f74acc52ab8fc07fa863d0aa50734910ec0ef2ad`; French `39fc2777822bbecab2d89bb23cbed40d9825ff4117897b8b025c02287f4ba845`; German `bfc64380bc24453f3460ffee6afbd7a3442b60dd26d5341c9fe0f1cca43216c3` |
| Size | 2,891 + 443 + 453 documents × 17 columns, 3.5 MB; the case study uses 3 columns (`document_type`, `generated_text`, `pii_spans`) and a fixed sample of 440 documents per language |

## What one row means

One synthetic financial document (a letter, form, e-mail, contract, payment message, XML or EDI file), with a list of labelled spans: where each value starts and ends in the text, and its type (29 types, such as `name`, `street_address`, `iban`, `company`, `date`). There is no target to predict: the labels are what a detector should find.

## Why this dataset

It has full documents with span labels in three of the course's languages, values that are made up for the purpose, and labels for values that a privacy policy keeps (companies, dates), so over-masking can be measured. Compared with NVIDIA Nemotron-PII (CC BY 4.0, English only), Gretel's English-only PII set (Apache-2.0) and the ai4privacy sets (non-commercial licence, excluded). See `reference/c24/m07/l01/DATASET-RESEARCH.md` in the course repository.

## Changes we made

None to the data. The notebook takes a fixed random sample (pandas `sample`, `random_state=24`) of 440 documents per language: the first 140 are the development part, the other 300 the test part. The masking policy groups the 29 labels: 24 are personal data to mask (11 groups), 5 are kept (company, date, time, date_time, swift_bic_code). Values that are template slots (`[Date]`, `MM/DD/YYYY`) count as placeholders.

The folder also holds `recordings/`: the answers of `chat-small` (gpt-6-luna on Azure) for three tasks on the test part (listing the personal data; choosing the document type; listing dates and companies), recorded on 2026-10-10. They contain values copied from the synthetic documents. `SHA256SUMS` lists their checksums.

## Limitations and cautions

- **The labels are incomplete and sometimes wrong.** The card says that the labels came from an NER library and an LLM judge. In the sample, 154 of 278 email-shaped strings have no label; role words such as `L'Employé` or `Sicherheitsnehmer` are labelled as names; template slots are labelled as values. Measured misses are a lower bound, and some measured over-masking is correct masking.
- **Synthetic values are not always realistic.** Only 32 of 54 IBANs pass the mod-97 checksum and 10 of 26 card numbers pass the Luhn check, so a detector that validates checksums misses values that a real document would not contain.
- **Generated text.** The documents were written by language models (Mistral-based); the names and addresses mix countries and languages (a "French" document can contain a Swedish address). Results do not transfer directly to real customer documents.
- **Small groups.** Card numbers, secrets, dates of birth and online IDs have fewer than 20 values per language in the test part.
- Financial documents only; no health or other special-category data.
