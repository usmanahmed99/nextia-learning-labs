# Dataset card: King County house sales, May 2014 – May 2015

Used by: C05-M09-L02 *Estimate house prices*, `C05/M09-L02-estimate-house-prices/estimate-house-prices.ipynb`

| Field | Value |
|---|---|
| Source | OpenML dataset 42092, `house_sales`, version 2: https://www.openml.org/d/42092 (file 21578898, `house_sales.arff`, MD5 `0208b93d87877d917afdc43987e7b4b4`, uploaded 2019-08-19) |
| Original | Kaggle, *House Sales in King County, USA*, by harlfoxem (2016-08-25): https://www.kaggle.com/datasets/harlfoxem/housesalesprediction |
| DOI | none |
| Publisher / creator | harlfoxem (Kaggle). The sales are public sale records of King County, Washington, USA; the uploader does not document how they were collected. |
| Licence | CC0 1.0 Public Domain (https://creativecommons.org/publicdomain/zero/1.0/). Checked on 2026-10-07: the OpenML API (`/api/v1/json/data/42092`) says `"licence": "CC0 Public Domain"`; the Kaggle API (`/api/v1/datasets/view/harlfoxem/housesalesprediction`) says `"licenseName": "CC0: Public Domain"`. The MD5 of our raw file matches the OpenML record. |
| Attribution text | CC0 needs no attribution; we give it anyway: "House Sales in King County, USA (harlfoxem, Kaggle 2016; OpenML 42092), CC0. Public sale records of King County, Washington." |
| Citation | harlfoxem (2016). *House Sales in King County, USA* [Dataset]. Kaggle. Via OpenML, dataset 42092 (version 2). |
| Version or access date | OpenML version 2; downloaded and checked 2026-10-07 |
| File used | `king_county_house_sales.csv.gz` (labs `C05/case-studies/data/`), made by `research/make_king_county.py` |
| SHA-256 | `0e2fd1937fbc724622e00fefebe060e28587882725663050c5c25fef74ce193c` |
| Size | 21,613 rows × 21 columns, 0.72 MB compressed |

## What one row means

One sale of one house in King County (Seattle and its suburbs) between 2014-05-02 and 2015-05-27, with the house's description. `price` (US dollars) is the target.

## Why this dataset

Real prices with a skewed target, strong location effects, a market that moves within a year, repeat sales of the same house, and a few data errors: the property that a lender's first estimate must handle. Compared in the research with the Ames housing data (De Cock 2011; `research/f2_ames.py`): 2,930 sales in one small town, 2006–2010, with 82 columns. Ames has richer columns, but we could not confirm an open licence on its source, its time split has only 341 test sales, and it has no coordinates. King County is CC0, larger (21,613 sales), and has latitude and longitude.

## Changes we made

- ARFF converted to CSV: the same 21 columns in the same order, the same 21,613 rows in the same order. No row removed or changed.
- `date` written as `YYYY-MM-DD` instead of `20141013T000000` (the time part was always `T000000`).
- gzip with mtime 0, so the file and its SHA-256 are reproducible.

The case study then changes one value in memory (not in the file): the house with 33 bedrooms and 1,620 sq ft (id 2402100895, sold 2014-06-25) is set to 3 bedrooms.

## Columns used

| Column | Meaning |
|---|---|
| `id` | house identifier (the same house can appear more than once) — used only to keep a house's sales together |
| `date` | sale date — used only for the split |
| `price` | target, US dollars |
| `bedrooms`, `bathrooms` | counts (0.5 = a toilet without a shower; 0.75 = a shower without a bath) |
| `sqft_living`, `sqft_lot` | living area and lot area, square feet |
| `floors` | number of floors (1.5 = a partial upper floor) |
| `waterfront` | 1 if on the water (163 houses) |
| `view` | quality of the view, 0–4 (0 = no rated view; 2,124 houses above 0) |
| `condition` | condition of the house, 1 (poor) – 5 (very good) |
| `grade` | King County building grade, 1–13: quality of construction and design (7 = average) |
| `sqft_above`, `sqft_basement` | area above ground and in the basement (`sqft_above + sqft_basement = sqft_living` in every row) |
| `yr_built`, `yr_renovated` | year built; year renovated (0 = never) |
| `zipcode` | US postal code (70 codes): a category, not a number |
| `lat`, `long` | latitude and longitude |
| `sqft_living15`, `sqft_lot15` | living and lot area of the 15 nearest neighbours |

## Known traps

- **No data dictionary from the uploader.** The meanings of `view`, `grade`, `condition`, `sqft_living15` and `sqft_lot15` come from King County Assessor terms and common descriptions of this dataset; `view` is sometimes wrongly described as "times viewed".
- **33 bedrooms** in one row (1,620 sq ft): a typing error for 3. 13 houses have 0 bedrooms and 10 have 0 bathrooms.
- **Codes that look like numbers:** `yr_renovated == 0` (never; 20,699 rows), `sqft_basement == 0` (no basement; 13,126 rows), `zipcode`.
- **Repeat sales:** 177 extra sales of 176 houses (one house sold 3 times); median price change from first to last sale +54.4% (houses bought, renovated, resold — the description does not change). Keep all sales of a house in one part of a split.
- **Skewed target:** prices from 75,000 to 7,700,000 dollars, median 450,000; 6.8% above 1 million. Use a log target and percentage errors.
- **Seasonal market:** fewer sales and lower prices in winter, higher in spring (median 476,500 in April 2015). A model trained in winter is too low in spring.
- **Non-market sales:** some very low prices (for example 130,000 for a house estimated at 420,000) are probably sales inside a family or forced sales; the data does not mark them.
- **Location and fairness:** zip code and location correlate with income and race in the United States. Lending rules (for example the Fair Housing Act and the Equal Credit Opportunity Act) and appraisal-bias concerns apply to any real use; the case study uses the model only as a first estimate before a human appraisal.
- **Age:** 2014–2015 prices; do not use them for today's market.
