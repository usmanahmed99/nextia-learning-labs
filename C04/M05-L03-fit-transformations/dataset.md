# Dataset card

This notebook uses the course's synthetic Larkfield help-desk export (CC0 1.0): `C04/data/customers.csv`, `tickets.csv` and `outcomes.csv`. The full card, with the source, licence and limitations, is [../data/dataset.md](../data/dataset.md).

The setup cells download the three files from the `main` branch of this repository and check their SHA-256 checksums. Then they run the course's finished scripts in [../pipeline](../pipeline) (extract, clean, build_features, split), as the learner does in Modules 3 to 5. The notebook then works with:

| File (in `ticket-data/`) | What it is |
|---|---|
| `data/model/train.csv`, `valid.csv`, `test.csv` | The modelling table split by time: 927, 227 and 215 rows. One row is one ticket, with 10 features known at creation and the target `escalated_72h`. |
| `data/clean/tickets.csv` | The clean tickets. The leakage experiments take two columns from it that a model must not use: `priority_now` and `first_reply_minutes`. |

| Field | Value |
|---|---|
| Licence | CC0 1.0 (public domain) |
| Why this dataset | It is the table that the learner builds in C04 Modules 3 to 5, so the notebook's numbers match the lesson. A public dataset would not have known leaky columns or the time split of the course. |

`../data/tickets_model.csv` (the modelling table with the two leaky columns) has the same rows and values; the notebook does not need it.
