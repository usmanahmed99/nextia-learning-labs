# Dataset card: King County house sales, for the case study *Serve a house-price model*

Used by: the case study *Serve a house-price model* (`starter.zip`, `finished.zip` in this folder). The full card of the data is [C05/case-studies/data/king_county_house_sales.md](../../C05/case-studies/data/king_county_house_sales.md); this card says how this case study uses it.

| Field | Value |
|---|---|
| Source | OpenML dataset 42092, `house_sales`, version 2: https://www.openml.org/d/42092. Original: *House Sales in King County, USA*, harlfoxem, Kaggle 2016 |
| Licence | CC0 1.0 Public Domain (https://creativecommons.org/publicdomain/zero/1.0/), checked 2026-10-07 |
| Attribution | "House Sales in King County, USA (harlfoxem, Kaggle 2016; OpenML 42092), CC0. Public sale records of King County, Washington." |
| File | `C05/case-studies/data/king_county_house_sales.csv.gz`, SHA-256 `0e2fd1937fbc724622e00fefebe060e28587882725663050c5c25fef74ce193c`, 21,613 sales from 2014-05-02 to 2015-05-27 |
| Collection | Public sale records of King County, Washington; the uploader does not document how they were collected |
| In the zips | Not the data: the trained model (`model/house_price.joblib`, 0.51 MB) and its card. `training/train.py` downloads the file above and checks its SHA-256 |

## How the case study uses it

- One fix: the house with 33 bedrooms and 1,620 sq ft is set to 3 bedrooms.
- Split by time, each house in one part: training = houses first sold before 2015-03-01 (16,959 sales); test = from 2015-03-01 (4,654 sales).
- The API's input limits come from the training data (minimum and maximum, rounded outward). The area check is the smallest box around every training house: latitude 47.15 to 47.78, longitude -122.52 to -121.31.
- The `rare_value` warning uses the 1st and 99th percentiles of seven size inputs in the training data.

## Checks that the case study runs

- `training/train.py` checks the SHA-256 of the data file and gives the test results of the machine learning course: MAPE 12.8%, 50.2% within 10%, 12.6% too high by 10% or more, median error +6.4%.
- The API refuses a model file whose SHA-256 is not the reviewed one, and a card that names another file.
- `tests/golden_houses.json`: three real test-set sales and the estimates that the API must give.

## Known gaps and biases

- Prices of 2014-15; the model lags a rising market (about 6% too low in spring 2015).
- No data dictionary from the uploader; meanings come from King County Assessor terms.
- Non-market sales (inside a family, forced sales) are not marked.
- Location correlates with income and race in the United States. The model is not for lending, underwriting or insurance decisions, and a real use needs a compliance review.
