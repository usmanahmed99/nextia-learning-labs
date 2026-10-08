# Dataset card: Online Retail II

Used by: C05-M09-L06 *Segment online-shop customers*, `C05/M09-L06-segment-online-shop-customers/segment-online-shop-customers.ipynb` (and the solution notebook)

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, dataset 502: <https://archive.ics.uci.edu/dataset/502/online+retail+ii> |
| Publisher / creator | Daqing Chen (donated 2019-09-20) |
| DOI | [10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D) |
| Licence | [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) |
| Attribution text | "Online Retail II" by Daqing Chen, UCI Machine Learning Repository, <https://doi.org/10.24432/C5CG6D>, licensed under CC BY 4.0. Changed by Nextia Learning: the two Excel sheets are joined into one gzip CSV file (see *Changes we made*). |
| Citation | Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D |
| Version or access date | The UCI file `online_retail_II.xlsx`, downloaded 2026-10-07 |
| File used | `online_retail_ii.csv.gz`, kept in labs `C05/case-studies/data/`: yes (CC BY 4.0 allows redistribution with attribution) |
| SHA-256 | `c5ab45f73700a1411440c2cd6b7d85611d22cdc72b3594c2d29d37261e977e4f` |
| Size | 1,067,371 rows × 8 columns; 15.0 MB compressed |

## What one row means

One line of an invoice of a UK-based online shop that sells gifts and homeware, many of them to wholesale customers, from 1 December 2009 to 9 December 2011. One invoice has many lines (one per product). There is no target: the case study builds one row per customer from the lines.

## Columns

| Column | Meaning |
|---|---|
| `Invoice` | The invoice number, 6 digits. A number that starts with `C` is a cancellation (a return). 6 lines start with `A` (debt adjustments). Read it as text. |
| `StockCode` | The product code, usually 5 digits, sometimes with a letter (`85123A`). Some codes are not products: see *Traps*. Read it as text. |
| `Description` | The product name. Missing on some lines. |
| `Quantity` | Units on the line. Negative on returns. |
| `InvoiceDate` | Date and time of the invoice. |
| `Price` | Price of one unit, in pounds sterling (£). |
| `Customer ID` | A 5-digit customer number. Missing on 243,007 lines (22.8%). In the CSV it is written as a decimal number (`13085.0`) because of the missing values. |
| `Country` | The customer's country (43 countries; United Kingdom 91.9% of the lines). |

## Why this dataset

It is real, messy transaction data with a clear business use: customer segments from recency, frequency and spend (RFM). It covers two years, so the segments built on the first 18 months can be checked against what the customers did in the next six months. Compared with: UCI Online Retail (the 2010–2011 part only: one year is too short for a forward check), and synthetic RFM data (no real cleaning work, no real future).

## Changes we made

- The source is one Excel workbook with two sheets, `Year 2009-2010` and `Year 2010-2011`. We joined them, in that order, into one table and wrote it as CSV with pandas (`index=False`), compressed with gzip (`mtime=0`, so the bytes are the same on every run). Script: `nextia-learning/reference/c05/case-studies/research/make_hosted.py`.
- `Invoice` and `StockCode` were read as text. No row and no value was removed or changed. `Customer ID` is written with `.0` (see above).

## Traps (the case study deals with each)

- **The two sheets overlap.** Both contain 1 to 9 December 2010 (22,523 lines in each). We kept both, as in the source, so these lines appear twice. Of the 34,335 exact repeated lines, 22,844 are from those nine days; the rest are repeats inside one sheet.
- **Missing customer ID** on 22.8% of the lines. These lines cannot be linked to a customer.
- **Returns** (`Invoice` starts with `C`): 19,494 lines, with a negative quantity.
- **Non-product codes**: `POST`, `DOT` (postage), `C2`, `C3` (carriage), `M`, `m` (manual), `D` (discount), `S` (samples), `B` (bad debt), `BANK CHARGES`, `ADJUST`, `ADJUST2`, `AMAZONFEE`, `CRUK` (a charity commission), `TEST001`, `TEST002`, `GIFT` and `gift_0001_*` (gift vouchers). `DCGS…` and `SP1002` are real products.
- **Price 0 or below** on 6,207 lines (free items and adjustments; only 61 of them are left after removing repeats, lines without a customer ID and non-product codes).
- **Huge mistaken orders**: customer 12346 ordered 74,215 storage jars (invoice 541431, 2011-01-18) and returned them 16 minutes later (C541433); customer 16446 did the same with 80,995 paper crafts on 2011-12-09.
- **The last month is short**: the data stops on 9 December 2011.

## Limitations and cautions

- One shop, 2009 to 2011, mostly UK customers, many of them small businesses that resell. Segments here say nothing about other shops or today's customers.
- Customer IDs are pseudonymous numbers; there are no names or contact details. Do not try to identify customers.
- Lines without a customer ID (often one-off buyers) are left out of the segments, so the segments describe registered customers only.
