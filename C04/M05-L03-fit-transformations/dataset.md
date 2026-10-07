# Dataset card

This notebook uses the course's synthetic Larkfield modelling table, `C04/data/tickets_model.csv` (1,369 rows × 16 columns, CC0 1.0). One row is one help-desk ticket created between 2026-01-05 and 2026-06-27, with 10 features known at creation, the target `escalated_72h`, and two leaky columns (`priority_now`, `first_reply_minutes`) kept on purpose for the leakage experiments. The full card, with the source, licence and limitations, is [../data/dataset.md](../data/dataset.md).

| Field | Value |
|---|---|
| File | [`../data/tickets_model.csv`](../data/tickets_model.csv) |
| SHA-256 | `cd0dffc4e29ac09d538da02c6d62633779022575f20c0ab8efb72abaade70d3e` |
| Licence | CC0 1.0 (public domain) |
| Why this dataset | It is the table that the learner builds in C04 Modules 3 to 5, so the notebook's numbers match the lesson. A public dataset would not have known leaky columns or the time split of the course. |

The notebook uses `tickets_model.csv` from its own folder if the file is there (the CI copies it there). If not, it downloads the file from the `main` branch of this repository and checks the SHA-256 checksum above.
