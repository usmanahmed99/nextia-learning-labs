# Dataset card: Boston 311 Service Requests from residents, counted per hour (January 2022 to July 2025)

Used by: AI System Design and Cost Engineering, case study *Cost and capacity plan from real demand data*, `cost-and-capacity-plan.ipynb`

| Field | Value |
|---|---|
| Source | https://data.boston.gov/dataset/311-service-requests (Analyze Boston, "311 Service Requests"; the yearly resources 2022, 2023, 2024 and 2025) |
| Publisher / creator | City of Boston, published on Analyze Boston |
| Licence | Open Data Commons Public Domain Dedication and License (PDDL) 1.0, https://opendatacommons.org/licenses/pddl/1-0/ |
| Attribution text | "311 Service Requests", City of Boston, Analyze Boston (data.boston.gov), ODC PDDL 1.0. Hourly counts by Nextia Learning. (PDDL does not require attribution; we give it anyway.) |
| Version or access date | Counted through the city's data store (CKAN `datastore_search_sql`) on 2026-10-10. The city revises its files, so this file is a fixed copy. |
| File used | `boston-311-hourly.csv`, kept in this folder: yes (PDDL allows it) |
| SHA-256 | 2ad790797890f35a67f4a9edd0b5c057e695edd30a0dd2b9f8ba51488f8238d6 |
| Size | 31,392 rows × 6 columns, 0.9 MB |

## What one row means

One hour in Boston local time, from `2022-01-01 00:00` to `2025-07-31 23:00`, also the hours without a request:

| Column | Meaning |
|---|---|
| `hour` | the start of the hour, local time (America/New_York, no offset) |
| `requests` | requests from residents in that hour: the sources `Citizens Connect App`, `Constituent Call` and `Self Service`, with repeated rows removed |
| `requests_raw` | the same before removing repeated rows |
| `busiest_minute` | the most requests from residents in one minute of that hour (repeats removed) |
| `busiest_minute_raw` | the same before removing repeats |
| `staff_requests` | requests that city staff created (`Employee Generated`, `City Worker App`) |

A repeated row has the same open time, request type and location as another row from residents. There is no target: the case study uses the counts as the demand of a public question-answering assistant (one request = one resident who asks).

## Why this dataset

It gives every number of the design pack's `demand.toml`: requests per day, the busiest hour against an average day, the busiest minute (the times are to the second), and growth over three and a half years. It is public domain and needs no personal data. Compared with: Wikimedia pageviews (CC0, but hourly only, so no busiest minute, and a worldwide audience with no local day); San Francisco 311 (the same licence, but the scaling course's case study already uses it); New York 311 (terms of use, not a named open licence).

## Changes we made

We did not copy any rows. The script `fetch_boston_311.py` (in the course's reference folder) asks the city's data store for counts per hour and per minute, keeps residents' sources only, removes repeated rows with `SELECT DISTINCT open_dt, type, location`, and writes one row for every hour. No IDs, types, addresses, coordinates or descriptions are in the file.

We stop at July 2025. From August 2025 the city moved requests to a new system with other columns (the resource "311 Service Requests - NEW SYSTEM"). From then on the old files hold only part of the requests, which would look like a fall in demand.

## Limitations and cautions

- The time is when the city's system recorded the request. Phone requests are often recorded to the minute (`:00` seconds).
- Local time without an offset: on the night of the spring clock change one hour has no requests, and in autumn one hour holds two hours of requests. Both are night hours with few requests.
- Some months have sudden runs of reports (August 2022, August and September 2023): up to 26 in one minute. The data cannot say whether they are residents, an app sending a backlog, or one person. The case study keeps them as the high case.
- A 311 request is a stand-in for a question to an assistant. Real assistants also get questions from people who would never file a request; the case study names this as its largest assumption.
- One city. Use the method for another city, not these numbers.
