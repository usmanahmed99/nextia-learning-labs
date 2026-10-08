# Dataset card: King County house sales, for C17-M06-L02 *Release a new house-price model*

Used by: C17-M06-L02 *Release a new house-price model* (`starter.zip`, `finished.zip` in this folder). The full card of the data is [C05/case-studies/data/king_county_house_sales.md](../../C05/case-studies/data/king_county_house_sales.md); this card says how this case study uses it. The case study continues C16-M08-L01 *Serve a house-price model* ([its card](../../C16/M08-L01-serve-a-house-price-model/dataset.md)).

| Field | Value |
|---|---|
| Source | OpenML dataset 42092, `house_sales`, version 2: https://www.openml.org/d/42092. Original: *House Sales in King County, USA*, harlfoxem, Kaggle 2016 |
| Licence | CC0 1.0 Public Domain (https://creativecommons.org/publicdomain/zero/1.0/), checked 2026-10-07 |
| Attribution | "House Sales in King County, USA (harlfoxem, Kaggle 2016; OpenML 42092), CC0. Public sale records of King County, Washington." |
| File | `C05/case-studies/data/king_county_house_sales.csv.gz`, SHA-256 `0e2fd1937fbc724622e00fefebe060e28587882725663050c5c25fef74ce193c`, 21,613 sales from 2014-05-02 to 2015-05-27 |
| In the zips | Not the data. The starter has C16's model (`model/house_price.joblib`, 0.51 MB); the finished project has two bundles with their models (0.51 and 0.52 MB). `training/train.py` and `replay/make_replay.py` download the file above and check its SHA-256 |
| Project code | MIT licence (`LICENSE` in each zip) |

## How the case study uses it

The data ends on 2015-05-27, so the case study chooses a "today" inside it. Each house goes where its first sale goes, as in C05 and C16:

| Part | Houses first sold | Sales | Use |
|---|---|---|---|
| Version 1 (kc-hgb-2015-02) learns from | before 2015-03-01 | 16,959 | C16's model, unchanged |
| Version 2 (kc-hgb-2015-03) learns from | before 2015-04-01 | 18,794 | one more month: March 2015 (1,835 sales) |
| The replay | 2015-04-01 to 2015-05-27 | 2,819 | requests to the API in the order of their sale dates; their prices arrive later. Neither version learned from them |

Two months are kept for the replay because May 2015 has only 646 sales (the data stops on 27 May). The replay is also version 2's test set: `training/train.py` reports the same comparison offline, and the shadow repeats it through the running API.

- One fix, as in C16: the house with 33 bedrooms and 1,620 sq ft is set to 3 bedrooms.
- 2 of the 2,819 replay requests are outside the API's limits (a lot of 1,164,794 sq ft; `sqft_living15` of 399) and get `422 invalid_request`. The contract does not change for a new model, so 2,817 requests are compared.

## The simulated export (a failure on purpose)

`training/simulate_export.py` writes `data/county-export-2015-04-01.csv.gz`: the same sales, but `yr_renovated` holds the build year where the house was never renovated (the course data and the API use 0). **The real county data never had this coding.** The case study uses it to show a realistic failure: a model trained on a changed export passes every offline test and every unit test, and the shadow catches it. The finished `training/train.py` refuses a file in which `yr_renovated` is never 0.

## Checks that the case study runs

- `training/train.py` checks the SHA-256 of the data file. For the default (version 1) it writes the same model file as C16, byte for byte (`8d0483d05cfc...`), so the learner's bundle digests equal the course's.
- `make_bundle.py` records nine parity cases per bundle; the API's start-up self-check and `scripts/check_release.py` compare them.
- `scripts/compare.py` joins the replay answers, the API's prediction log and the sale prices.

## Known gaps and biases

- Prices of 2014-15; both versions lag a rising market (median error +7.4% and +6.9% on the replay: too low).
- Estimates of 1 million USD or more are weak and move most between versions.
- No data dictionary from the uploader; meanings come from King County Assessor terms.
- Location correlates with income and race in the United States. The model is not for lending, underwriting or insurance decisions; the zip-code check in the release looks at the size of changes by area, which is not a fairness review.
