# Dataset card: Wholesale customers

Used by: the case study *Find wholesale buyer types* in the machine learning course, `C05/M09-L07-find-wholesale-buyer-types/find-wholesale-buyer-types.ipynb` (and the solution notebook)

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, dataset 292: <https://archive.ics.uci.edu/dataset/292/wholesale+customers> |
| Publisher / creator | Margarida Cardoso (donated 2014-03-30) |
| DOI | [10.24432/C5030X](https://doi.org/10.24432/C5030X) |
| Licence | [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) |
| Attribution text | "Wholesale customers" by Margarida Cardoso, UCI Machine Learning Repository, <https://doi.org/10.24432/C5030X>, licensed under CC BY 4.0. Changed by Nextia Learning: recompressed as gzip (see *Changes we made*). |
| Citation | Cardoso, M. (2013). Wholesale customers [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5030X |
| Version or access date | The UCI file `Wholesale customers data.csv`, downloaded 2026-10-07 |
| File used | `wholesale_customers.csv.gz`, kept in labs `C05/case-studies/data/`: yes (CC BY 4.0 allows redistribution with attribution) |
| SHA-256 | `c3229cf9d5df7ff307cc554b2a30afa618b0875ba836f1434b09d2d1ca8ea390` |
| Size | 440 rows × 8 columns; 7 KB compressed |

## What one row means

One customer of a wholesale food distributor in Portugal, with the customer's spending in one year on six product categories. There is no target. `Channel` (the kind of business) is the label the distributor already uses; the case study keeps it out of the clustering and uses it afterwards as a check.

## Columns

| Column | Meaning |
|---|---|
| `Channel` | 1 = Horeca (hotel, restaurant or café), 298 customers; 2 = Retail (a shop), 142. |
| `Region` | 1 = Lisbon (77), 2 = Oporto (47), 3 = other regions (316). |
| `Fresh`, `Milk`, `Grocery`, `Frozen`, `Detergents_Paper`, `Delicassen` | Spending in one year on each category, in "monetary units" (m.u.; the source does not name the currency). `Delicassen` is the source's spelling of delicatessen. |

## Why this dataset

It is small and real, the spending is strongly skewed (skew 2.6 to 11.2), and it has an existing label (`Channel`) that clustering can be compared with. This makes the effect of scaling and of a log visible, and it lets the learner see where a cluster agrees with the business's own label and where it does not. Compared with: the UCI Online Retail II data (used in the case study *Segment online-shop customers*, so a second dataset with a different lesson was preferred) and synthetic blobs (no real skew, no real label).

## Changes we made

The source CSV was read with pandas and written again as CSV (`index=False`), compressed with gzip (`mtime=0`). Values, column names and row order are unchanged. Script: `nextia-learning/reference/c05/case-studies/research/make_hosted.py`.

## Traps (the case study deals with each)

- **Strong skew**: a few customers spend 10 to 50 times the median. Distance-based methods without a log are decided by them.
- **Tiny values**: some customers spend 3 m.u. a year on a category. After a log these become the most extreme values (17 of the 18 customers more than 3 SDs from the mean are on the low side).
- **Correlated columns**: `Grocery` and `Detergents_Paper` have a correlation of 0.92, so together they count almost twice.

## Limitations and cautions

- 440 customers of one distributor, one year (the source gives no year), one country. Conclusions are tentative.
- No dates, no number of orders, no customer size: spending mixes "how big" with "what kind".
- The source does not say how `Channel` was assigned or how old it is.
