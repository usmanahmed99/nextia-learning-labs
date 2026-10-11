# Dataset card: openFDA food recall enforcement reports

Used by: MCP: Connect AI Applications to Tools and Data, case study *An MCP server over a real open dataset*, project `food-recalls` (starter and finished)

| Field | Value |
|---|---|
| Source | openFDA, food enforcement reports: https://open.fda.gov/apis/food/enforcement/ (bulk file https://download.open.fda.gov/food/enforcement/food-enforcement-0001-of-0001.json.zip) |
| Publisher / creator | U.S. Food and Drug Administration (FDA), through openFDA |
| Licence | Public domain, with a Creative Commons CC0 1.0 Universal dedication: https://open.fda.gov/license/ |
| Attribution text | "Source: U.S. FDA food recall enforcement reports, via openFDA (public domain). The data is not validated by FDA." (Not required by CC0; we give it so readers can check the source.) |
| Version or access date | openFDA export of 2026-10-06 (`meta.last_updated`), downloaded 2026-10-10. openFDA replaces the file every week under the same name. |
| File used | `food-enforcement-2026-10-06.json.zip` (the original zip, renamed), kept in `data/` of the labs folder: yes (CC0 allows it) |
| SHA-256 | `fa59ccc9642b4e47f979b9e4f206e80afcd48b7297c68805dc811826d3fbcb9b` |
| Size | 29,471 records × 25 fields; 5.9 MB zipped (5,853,780 bytes), 39.9 MB as JSON. After our checks: 29,424 recalls in 7,884 recall events, reported 2012-06-20 to 2026-09-30. |

## What one row means

One row is one recalled product in an FDA enforcement report: its recall number (for example `H-1393-2026`), the firm, the product, the reason, the classification (Class I is the most serious: a reasonable chance of serious harm), the status (Ongoing, Completed, Terminated) and the dates. One recall event can cover many products, so many rows can share an `event_id` (one event has 409).
There is no target: the case study answers questions, it does not predict.

## Why this dataset

The case study needs real public records that people ask about one at a time, with stable IDs for resource URIs, and with sizes that make bounds matter. This file has all three: a recall number for each record, a median record of 1,100 characters and a largest of 44,645, and searches that match 1 record or 7,487.
We compared it with two other candidates (`reference/c28/m08/l01/DATASET-RESEARCH.md` in the course repository):

- **CPSC Recalls** (consumer products, saferproducts.gov API): a good fit for a retailer, but the API pages state no licence or terms of use for the data. Rejected: unclear terms.
- **openFDA drug enforcement reports** (same licence, 18,002 records, 3.8 MB zipped): clear and small, but drug recalls are harder to explain to a first-time learner and invite medical questions. Rejected for the audience.

## Changes we made

- **Left out 47 records** (0.16%) whose `recall_number` does not have FDA's form `X-0000-0000`: one is empty, others are typing errors such as `F1462-2014` or `F-1772`. A stable URI needs a valid, unique ID, and we do not invent IDs. `scripts/get_data.py` lists them in `data/excluded.jsonl`. One of them is recent (reported 2026-09-30, with an empty number).
- **Dropped fields:** each firm's street address and postal code (`address_1`, `address_2`, `postal_code`; not needed to answer about a recall), the `openfda` field (empty for every food record) and `product_type` (always `Food`). City, state and country stay.
- **Joined** `more_code_info` to `code_info`; **wrote dates** as `YYYY-MM-DD` instead of `YYYYMMDD`.
- No other change. Texts are as FDA published them, including capital letters and `***` marks.

## Limitations and cautions

- **Enforcement reports are not all recalls,** and the file lags: a recall appears after FDA classifies it. "No recall found in this data" never means "safe".
- **openFDA says:** "Do not rely on openFDA to make decisions regarding medical care … you should assume all results are unvalidated." The server repeats this in its instructions and in every recall.
- **A snapshot.** This copy stops at reports of 2026-09-30. Newer recalls exist; `python -m scripts.get_data --latest` fetches openFDA's current file (a new checksum).
- **Words, not products.** The search matches words in the product text, which often lists ingredients: "peanut butter" also finds ice cream sandwiches that contain peanut butter.
- **Firm names are business names.** Some firms are named after people. Do not combine the data with other sources to find out about people.
- **Uneven years.** 2015–2017 have about 3,000 reports each, other years 1,000–2,300. Only products under FDA's authority in the United States are in it.
