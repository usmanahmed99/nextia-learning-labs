# Dataset card: synthetic support tickets

Used by: Modules 4 to 6 of this course and the final assignment, and `C02/M06-L01-notebook-discipline/notebook-discipline.ipynb`

| Field | Value |
|---|---|
| Source | Written for this course by Nextia. Not taken from any real system. |
| Publisher / creator | Nextia |
| Licence | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) |
| Attribution text | None needed. "Synthetic support tickets, Nextia Learning" is welcome. |
| Version or access date | 1.0, 2026-10-06 |
| File used | `tickets.csv`, `tickets.json`, `tickets-excel.csv`, `tickets-v2.csv` and `tickets-v2.json`, kept in `data/`: yes |
| SHA-256 | `tickets.csv` 82e3fb4fa6d94a47b9a7b05d940a088596363e4dd11e89bf82ed486bd2325a1a<br>`tickets.json` a801f505e3d91ff79cefee9c72e53b5f48e983ee152305b7f04e3ac882dd9946<br>`tickets-excel.csv` cf0fbbce193bb1a595ce9207cc3f004aeedb118008e4ffa35585fda2f1167a95<br>`tickets-v2.csv` 814d8cc052830430fe98b2b765ff6baeea4b9c819187b5cfbd0428c5e81735d3<br>`tickets-v2.json` 7fca56525186e764c63cf7e8c82259dee715f9667bbf9f444c85279f22758c0a |
| Size | Version 1: 15 rows × 5 columns. Version 2: 20 rows × 6 columns. Under 4 KB per file. |

## What one row means

One support ticket: its ID, status (`open`, `pending` or `closed`), category, priority (1 is the most urgent, 3 the least) and a short subject. There is no target column; the course uses the data to practise validation and reporting.

## Why this dataset

The lessons of this course teach how to read, validate and report on records of mixed quality. The data must contain each kind of problem exactly once, in a file small enough to read completely, so that a learner can predict every result by hand. Public help-desk datasets were considered and rejected: they are large, often contain personal data in free text, and their problems are not controlled.

Nine rows are valid, three of them only after cleaning (`Open ` with a space and capital letter, `LOGIN`, and the lower-case ID `t-1015`). Six rows each have one problem:

| Row | Problem |
|---|---|
| 7 | Unknown status `opne` |
| 8 | Missing ID |
| 9 | Priority `high` is not a number |
| 11 | Priority `5` is out of range |
| 13 | Duplicate of row 3 (T-1003) |
| 14 | Missing category |

## Version 2 (final assignment)

`tickets-v2.csv` and `tickets-v2.json` add two columns: `channel` (`email`, `phone` or `chat`) and `subject`. Twelve rows are valid, four of them only after cleaning (`Email `, a priority ` 3 ` with spaces, `LOGIN` and `Chat`). Eight rows each have one problem: an unknown channel (`fax`, row 5), an empty subject (row 6), a missing channel (row 8), priority `0` (row 9), a duplicate ID that differs only in capital letters (`t-2001`, row 10), an unknown status (`resolved`, row 11), a missing ID (row 16) and priority `two` (row 17). The CSV file is saved as a spreadsheet export (byte order mark, CRLF). Two subjects contain non-English letters.

## Changes we made

- One subject contains a non-English letter (`Müller`, row 12), so that reading the file with the wrong text encoding shows a visible error.

- `tickets.json` has the same rows as `tickets.csv`. Numeric priorities are JSON numbers, as a web service would send them; `high` stays a string.
- `tickets-excel.csv` has the same rows as `tickets.csv`, saved as a spreadsheet program does: with a UTF-8 byte order mark and Windows line endings (CRLF). Module 5 uses it to find a parsing bug.

## Limitations and cautions

The data is invented and very small. It shows the kinds of problem that real ticket data has, not how often they occur. Do not use it to draw conclusions about real help desks.
