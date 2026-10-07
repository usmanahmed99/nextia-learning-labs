# Dataset card: credit_default_taiwan.csv.gz

Used by C05-M09-L03 *Predict credit-card default* (labs `C05/M09-L03-predict-credit-card-default/`).

| | |
|---|---|
| **Source** | UCI Machine Learning Repository, *Default of Credit Card Clients*, https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients (file `default of credit card clients.xls`) |
| **DOI** | 10.24432/C55S3H |
| **Creator** | I-Cheng Yeh (donated to UCI on 2016-01-25) |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the UCI page (checked 2026-10-07) |
| **Accessed** | 2026-10-07 |
| **Hosted file** | labs `C05/case-studies/data/credit_default_taiwan.csv.gz` (gzip CSV, 0.98 MB) |
| **SHA-256** | `a773cfc32f6759261cebfdfdc4f744bce1b247a583fe7c06363a12702c98f727` |
| **Rows, columns** | 30,000 rows, 25 columns |
| **One row** | One credit-card client of a bank in Taiwan: the credit limit, five personal facts, and six months (April to September 2005) of repayment status, bill amount and amount paid. |
| **Target** | `default`: 1 if the client defaulted on the payment due in the next month (October 2005), else 0. 6,636 defaults (22.1%). |

## Attribution text (required by CC BY 4.0)

> Data: "Default of Credit Card Clients" by I-Cheng Yeh, UCI Machine Learning Repository, https://doi.org/10.24432/C55S3H, licensed under CC BY 4.0. Changed by Nextia Learning: converted from XLS to gzip CSV, the first header row removed and the target column renamed (see the card).

## Citation

- Yeh, I. (2009). *Default of Credit Card Clients* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C55S3H
- Yeh, I.-C., & Lien, C.-H. (2009). The comparisons of data mining techniques for the predictive accuracy of probability of default of credit card clients. *Expert Systems with Applications*, 36(2), 2473–2480.

## Exact changes made to the source file

1. Read the sheet with the second row as the header (the first row holds the labels `X1` … `X23`, `Y`, which are dropped).
2. Renamed the target column `default payment next month` to `default`.
3. Wrote all 30,000 rows and 25 columns, unchanged in value and order, as UTF-8 CSV without an index, gzip-compressed with `mtime=0` (so the file and its checksum are reproducible). Script: `nextia-learning/reference/c05/case-studies/research/make_hosted.py`.

The column `PAY_0` keeps its source name in the file. The notebook renames it to `PAY_1` (see the traps).

## Columns used in the case study

| Column | Meaning | Use |
|---|---|---|
| `ID` | Row number of the source file | Not an input |
| `LIMIT_BAL` | Credit limit of the card, in NT dollars (family and supplementary cards included) | Input |
| `SEX` | 1 = male, 2 = female | **Sensitive: never an input, only for slice checks** |
| `EDUCATION` | 1 = graduate school, 2 = university, 3 = high school, 4 = others | Input (codes 0, 5, 6 grouped into 4) |
| `MARRIAGE` | 1 = married, 2 = single, 3 = others | **Sensitive: never an input, only for slice checks** |
| `AGE` | Age in years | **Sensitive: never an input, only for slice checks** |
| `PAY_0`, `PAY_2` … `PAY_6` | Repayment status in September, August, …, April 2005: −1 = paid duly; 1 … 9 = payment delay of 1 … 9+ months (−2 and 0 are not documented) | Inputs, as categories |
| `BILL_AMT1` … `BILL_AMT6` | Bill statement amount, September … April 2005, NT dollars | Inputs (signed log, then scaled) |
| `PAY_AMT1` … `PAY_AMT6` | Amount paid in September … April 2005, NT dollars | Inputs (signed log, then scaled) |
| `default` | Target, see above | Target |

## Known traps

- **Undocumented codes.** `EDUCATION` has 0 (14 rows), 5 (280) and 6 (51); `MARRIAGE` has 0 (54). The repayment status has −2 and 0, which the source does not define (a common reading is −2 = no card use, 0 = the minimum was paid; treat it as unconfirmed).
- **`PAY_0` is the first month.** The status columns are `PAY_0, PAY_2, …, PAY_6`; there is no `PAY_1`, while the bill and payment columns are numbered 1 to 6. `PAY_0` is September and matches `BILL_AMT1` and `PAY_AMT1`.
- **September is coded differently.** Code 1 (one month late) appears in 12.3% of `PAY_0` values and in 0.09% of `PAY_2`; 1,221 clients have `PAY_0 = 1` and `PAY_2 = −2`. Do not compare the months' status codes as if they meant the same.
- **Status codes are categories, not amounts.** −2, −1 and 0 are not ordered on one scale with the delays. As numbers they give a worse model (CV AP 0.495 against 0.542 as categories, in the case study).
- **Negative bills.** 590 clients have a negative September bill (they paid more than they owed).
- **Clients with no bill.** 866 clients have a bill of 0 in all six months, and 36.6% of them are marked as defaulting: check the meaning of the target for such rows before you rely on it.
- **Repeated profiles.** 35 rows repeat another row in every column except `ID` (mostly clients with no activity). They have different IDs, so the case study keeps them.
- **Skewed amounts.** Bill and payment amounts have long right tails (skew of `PAY_AMT1`: 14.7).
- **Sensitive data and proxies.** Sex, marital status and age are personal data. Even when they are left out of the inputs, other columns can stand in for them: the credit limit is much lower for clients aged 21–25 (median 50,000 against 140,000–180,000 for 26–50), so young clients are flagged more often.
- **One snapshot, one place, one time.** All rows are from one bank in Taiwan in 2005, during a period of high card debt. There is no date per row, so no time-based check is possible.
