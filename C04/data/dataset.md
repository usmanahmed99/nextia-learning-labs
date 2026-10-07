# Dataset card: Larkfield help-desk export (C04)

Used by: C04 Modules 1 to 6 and the final assignment, and `C04/M05-L03-fit-transformations/fit-transformations.ipynb`

| Field | Value |
|---|---|
| Source | Written for this course by Nextia with [`C04/generate.py`](../generate.py). Not taken from any real system. |
| Publisher / creator | Nextia |
| Licence | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) |
| Attribution text | None needed. "Synthetic Larkfield help-desk export, Nextia Learning" is welcome. |
| Version or access date | 1.0, generated 2026-10-06 with Python 3.14.6, seed 2026 |
| File used | All files below, kept in `data/`: yes |
| SHA-256 | `customers.csv` 7b437642f0095524f8311f67a7caeb17100d23eed92618b9cf012cd3d3b79993<br>`tickets.csv` 9c47e08cf2ec5977733d32cc21eb97d0dd01b021d1f5fbf7ec31fef6279b1a28<br>`outcomes.csv` 67b4d9d9275b32061a8888050c351df7314054c11ee1ce29e856c1d5403d0653<br>`tickets-2026-08-01.csv` d3ccdb946d4896be51c2da32f0ff649dc6768cd5ac69b573bc83360a9183fdef<br>`tickets_model.csv` cd0dffc4e29ac09d538da02c6d62633779022575f20c0ab8efb72abaade70d3e |
| Size | customers 240 rows × 4 columns; tickets 1,417 rows × 11 columns; outcomes 1,874 rows × 6 columns; tickets-2026-08-01 40 rows × 11 columns; tickets_model 1,369 rows × 16 columns. Under 200 KB per file. |

## What one row means

Larkfield is a fictional online shop for home and garden products. The files are the export of its help-desk system on 2026-07-01 at 06:00 (the **snapshot**).

- `customers.csv`: one customer (segment, region, the date they joined).
- `tickets.csv`: one support ticket, created between 2026-01-05 and 2026-06-30. Some columns were filled in after the ticket was created.
- `outcomes.csv`: one event in a ticket's life (`escalated`, `resolved` or `reopened`), with the time it was recorded.
- `tickets_model.csv`: the modelling table that the course builds in Modules 3 to 5, one row per ticket. The target is `escalated_72h`: 1 if a senior agent took the ticket within 72 hours of creation. It also keeps two columns that a model must **not** use, `priority_now` and `first_reply_minutes`, for the leakage exercise in the notebook.
- `tickets-2026-08-01.csv`: the next month's export, after a help-desk update changed its schema (Module 6).

## Why this dataset

C04 teaches how to query, clean and prepare data without quiet mistakes. The data must contain each kind of mistake, in known amounts, so that every result in a lesson can be checked exactly. Public help-desk datasets were considered and rejected: they are larger than needed, often contain personal data in free text, rarely have a related customer table and outcome history, and their problems are not controlled. The C02 tickets were too small (15 rows) for joins, time-based splits and a model.

## Problems added on purpose

| Table | Problem | Count |
|---|---|---|
| customers | `region` missing | 9 customers |
| customers | `segment` spelled `Trade` instead of `trade` | 3 customers |
| tickets | Exact duplicate rows (export page overlap) | 14 rows |
| tickets | `customer_id` missing (guest checkout) | 12 rows |
| tickets | `customer_id` not in customers (deleted accounts C-0241 to C-0244) | 9 rows |
| tickets | `channel` spellings `Email`, `EMAIL`, ` chat`, `webform` | 40 rows |
| tickets | `channel` missing | 38 rows |
| tickets | `order_value` in cents, not dollars (old web form, before 2026-02-01) | web form rows of January |
| tickets | `order_value` is `-1`, meaning "unknown" | 11 rows |
| tickets | `order_value` missing because the ticket is about an account, not an order (a meaningful gap) | 188 rows |
| tickets | `word_count` 0 (attachment only; valid) and 48,210 (a pasted log) | 7 and 1 rows |
| tickets | Created before the customer joined | 3 rows |
| tickets | Year typed as 2036 | 1 row |
| tickets | `priority_now`, `first_reply_minutes`, `closed_at` are filled in after creation (leakage) | all rows |
| outcomes | The same event logged twice by a retry (new `outcome_id`) | 30 events |
| outcomes | Events of tickets that are not in tickets.csv | 4 events |
| outcomes | Reopened and resolved in the same second (ties) | some reopened tickets |

The escalation rate rises after 2026-05-01, when a new warranty policy starts. A time-based split shows this change; a random split hides it.

## Changes we made

None after generation. `generate.py` writes every file except `tickets_model.csv`, which is the output of the course's reference pipeline (extract, clean, build features) with the two leaky columns joined back.

## Limitations and cautions

- The data is synthetic. Relationships between columns are simple and were chosen for teaching; do not draw conclusions about real help desks from it.
- The escalation model that the course builds is a demonstration of data preparation, not a useful product. Its scores are modest on purpose.
- Python's `random` module produces the same numbers for the same seed across recent versions, but this is not guaranteed forever. The checksums above detect any change.
