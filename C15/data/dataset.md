# Dataset card: the web form's export

Used by: Grace's bug report and Module 4 of the course, `web-form-export.csv` (also in `data/` of every snapshot)

| Field | Value |
|---|---|
| Source | Written for this course by Nextia. Not taken from any real system. |
| Publisher / creator | Nextia |
| Licence | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) |
| Attribution text | None needed. "Synthetic support tickets, Nextia Learning" is welcome. |
| Version or access date | 1.0 |
| File used | `web-form-export.csv`, kept in `data/`: yes |
| SHA-256 | `ec488ab92ad600aaf073cafe991bf69aecfd98eebc21c693c577ef0b17ec50f6` |
| Size | 12 rows × 5 columns, under 1 KB |

## What one row means

One support ticket from Larkfield's new web form: its ID, status, category, priority (1 is the most urgent) and a short subject. The columns are the same as in the Python course's `tickets.csv`. There is no target column.

## Why this dataset

Grace's bug must be visible in one short file that a learner can read completely and check by hand. All 12 rows are valid, so no warning hides the problem. The same teams are written in different ways, as people and forms do: `login`, `Login`, `LOGIN` and the form's own name `Sign-in`; `billing`, `Billing ` (with a space) and `Invoice`; `shipping` and `Delivery`. The correct open report is account 1, billing 3, login 4 and shipping 2. Public help-desk data was not used: it is large, it often has personal data in its text, and its spellings are not controlled.

## Changes we made

None. The file was written for the course.

## Limitations and cautions

The data is invented and very small. It shows one kind of problem, not how often it happens. Do not use it to draw conclusions about real help desks.
