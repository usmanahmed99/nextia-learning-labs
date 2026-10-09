# Dataset card: Default of Credit Card Clients (Taiwan, 2005)

Used by: C06-M08-L02 *Deep network or gradient boosting?*, `deep-network-or-gradient-boosting.ipynb` (and the `-solution` notebook)

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, *Default of Credit Card Clients*, https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients (DOI 10.24432/C55S3H) |
| Publisher / creator | I-Cheng Yeh (donated to UCI on 2016-01-25) |
| Licence | Creative Commons Attribution 4.0 International ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)), as stated on the UCI page (checked 2026-10-08) |
| Attribution text | Data: "Default of Credit Card Clients" by I-Cheng Yeh, UCI Machine Learning Repository, https://doi.org/10.24432/C55S3H, licensed under CC BY 4.0. Changed by Nextia Learning: converted from XLS to gzip CSV, the first header row removed and the target column renamed. |
| Version or access date | Accessed 2026-10-07 (hosted copy made for the machine learning course); licence re-checked 2026-10-08 |
| File used | `credit_default_taiwan.csv.gz`, kept in this repository at `C05/case-studies/data/` (shared with the machine learning course's case study); the notebook downloads it from there: yes |
| SHA-256 | `a773cfc32f6759261cebfdfdc4f744bce1b247a583fe7c06363a12702c98f727` |
| Size | 30,000 rows × 25 columns, 0.98 MB (gzip CSV) |

## What one row means

One credit-card client of one bank in Taiwan: the credit limit, five personal facts, and six months (April to September 2005) of repayment status, bill amount and amount paid. The target `default` is 1 if the client did not make the payment due in October 2005 (6,636 defaults, 22.1%).

## Why this dataset

The case study asks whether a neural network is worth its cost on a **table of facts that people chose**. This table has the three things that make a network work harder than gradient boosting: codes written as numbers, very skewed amounts, and a modest size (30,000 rows). The machine learning course already framed it (split, costs, metric, sensitive columns), so the case study changes only the model and compares with that course's published numbers. Alternatives compared (all CC BY 4.0, UCI): Adult / Census Income (no business decision; used only as a second check in the authors' script), Bank Marketing (its lessons are a leak and drift, which would distract), Covertype (581,012 rows, too large for a 10-minute CPU notebook with many seeds). Details: `nextia-learning/reference/c06/m08/l02/DATASET-RESEARCH.md`.

## Changes we made

None beyond the hosted copy's changes (XLS to gzip CSV, first header row removed, target renamed to `default`; script `nextia-learning/reference/c05/case-studies/research/make_hosted.py`). In the notebook: `PAY_0` is renamed `PAY_1`, and the undocumented education codes 0, 5 and 6 are grouped into 4 ("others"). No sampling.

## Limitations and cautions

- One bank, one period (2005, during a time of high card debt), no dates: no time-based check is possible.
- Undocumented codes: repayment status −2 and 0, education 0/5/6, marital status 0.
- Sensitive data: sex, marital status and age are personal facts. The notebook never uses them as inputs. Other columns can stand in for them (the credit limit is much lower for clients aged 21–25).
- Default means "did not make the next payment". It is not a judgement of a person's honesty.
- Do not use models from this data for real credit decisions.
