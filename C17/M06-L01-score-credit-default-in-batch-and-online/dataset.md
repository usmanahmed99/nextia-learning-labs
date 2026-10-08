# Dataset card: Default of Credit Card Clients, for the case study *Score credit default in batch and online*

Used by: the case study *Score credit default in batch and online* (`starter.zip`, `finished.zip` in this folder). The full card of the data is [C05/case-studies/data/credit_default_taiwan.md](../../C05/case-studies/data/credit_default_taiwan.md); this card says how this case study uses it.

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, *Default of Credit Card Clients*, https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients, DOI 10.24432/C55S3H. Creator: I-Cheng Yeh |
| Licence | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), as stated on the UCI page (checked 2026-10-07) |
| Attribution | "Default of Credit Card Clients" by I-Cheng Yeh, UCI Machine Learning Repository, https://doi.org/10.24432/C55S3H, licensed under CC BY 4.0. Changed by Nextia Learning: converted from XLS to gzip CSV, the first header row removed and the target column renamed to `default`. |
| File | `C05/case-studies/data/credit_default_taiwan.csv.gz`, SHA-256 `a773cfc32f6759261cebfdfdc4f744bce1b247a583fe7c06363a12702c98f727`, 30,000 clients, 25 columns |
| In the zips | The same file, unchanged, in `credit-default-service/data/`, with `data/README.md` (the attribution and the licence). The project code is MIT; the data stays CC BY 4.0. |

## How the case study uses it

- `training/train.py` renames `PAY_0` to `PAY_1` (it is September) and splits the clients at random, stratified by `default` (seed 0): train 18,000, validation 6,000, test 6,000, as in the case study *Predict credit-card default* of the machine learning course. Inputs: 20 columns (education, six repayment statuses, the credit limit, six bills, six payments). Education codes 0, 5 and 6 become 4 (others) inside the pipeline.
- **Not inputs, and not in the monthly file:** `SEX`, `MARRIAGE`, `AGE` (sensitive) and `default` (the target). `scripts/export_month.py` writes only `client_id` and the 20 inputs.
- **The monthly file** `data/clients-2005-09.csv` holds all 30,000 clients. The data has one statement month, so this "month" contains the clients that the model was trained and tested on; it shows how the serving works, not how well the model does on new clients (the test set did that once).
- **The contract's ranges** are the smallest and largest values in the 30,000 rows: credit limit 10,000 to 1,000,000; bills -339,603 to 1,664,089 (any month); payments 0 to 1,684,259; statuses -2 to 8 (9 is documented but never occurs); education 0 to 6.
- `scripts/export_month.py --limit-in-thousands` writes a changed copy (the credit limit divided by 1,000) for the failure in the case study. It is not real data.

## Checks that the case study runs

- `training/train.py` checks the SHA-256 of the data file and gives the results of the machine learning course: threshold 0.17 (cost 5 for a missed default, 1 for a false alarm), test ROC AUC 0.770, 38.2% flagged, precision 0.406, recall 0.701.
- The bundle's 12 parity cases (6 real clients, 6 made at the edges of the contract) get the same score from training, the batch job and the API, within 1e-9.

## Known gaps and biases

- One bank in Taiwan, April to September 2005, during a period of high card debt. No date per row, so no time-based test.
- Undocumented codes: education 0, 5, 6; repayment status -2 and 0.
- 866 clients have no bill in any month, and 36.6% of them are marked as defaulting: check the meaning of the target for such rows.
- Young clients are flagged more often, mostly through their lower credit limits. The model is for a supportive early-help call, not for refusing credit, limits or prices.
