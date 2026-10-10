# Dataset card: NYC 311 requests of two departments, January to June 2025

Used by: the case study *Add sign-in and roles to an existing API* (the authentication course): the API in this project (`data/service_requests_2025h1_v2.db`) and its tests (`tests/fixture_rows.csv`, 30 transport rows, and `tests/fixture_rows_parks.csv`, 12 parks rows). Version 2 of the database of the API course's case study: the same 109,915 transport (DOT) requests, and 48,743 parks (DPR) requests of the same months.

| Field | Value |
|---|---|
| Source | [311 Service Requests from 2020 to Present](https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9), NYC Open Data, dataset `erm2-nwe9` |
| Publisher | City of New York, 311 and the agencies that handle the requests (here the Department of Transportation, DOT, and the Department of Parks and Recreation, DPR) |
| Licence | No restrictions on use. NYC Open Data: "There are no restrictions on the use of Open Data." NYC Administrative Code §23-502(d) allows the city to ask users to name the source and version, and to describe changes, which this card does. |
| Attribution text | Data: NYC Open Data, 311 Service Requests (erm2-nwe9), agencies DOT (snapshot of 2026-10-07) and DPR (snapshot of 2026-10-10), cleaned by Nextia Learning. |
| Version | DOT: pulled on 2026-10-07 through the city's SODA API, created from 2024-01-01 to 2025-06-30, 315,424 requests, 20 columns; frozen copy `C04/case-studies/data/nyc311_dot_2024-01_2025-06.csv.gz` in the Nextia Learning labs repository, SHA-256 `31240271a6961024526bca4750f09ed6297b24fee1dcc5d506004102066cf9e2`. DPR: pulled on 2026-10-10 07:17 UTC through the same API (`$where=agency='DPR' AND created_date >= '2025-01-01T00:00:00' AND created_date < '2025-07-01T00:00:00'`, the same 20 columns), 48,748 requests; frozen copy `C23/M07-L02-add-sign-in-and-roles-to-an-existing-api/data/nyc311_dpr_2025h1.csv.gz`, SHA-256 `df10c9ba1f1b81a5c9b6013624298b1ff818702b33f771192374b7ba8b0f986e`. |
| File used | `service_requests_2025h1_v2.db.gz` in the same labs folder, SHA-256 in `scripts/get_db.py`. `scripts/build_db.py` makes the same data from the two frozen copies. |
| SHA-256 | `service_requests_2025h1_v2.db.gz`: `f6d4201fd8494690dc9f3aec76c295ce1bec79c846c46d9b799b04692adabd8c` (also in `scripts/get_db.py`); `nyc311_dpr_2025h1.csv.gz`: `df10c9ba1f1b81a5c9b6013624298b1ff818702b33f771192374b7ba8b0f986e` |
| Size | 158,658 rows × 16 columns (transport 109,915, parks 48,743); 65 MB as SQLite, 13 MB compressed |

## What one row means

One request that a person made to 311 and that the city sent to its transport department (a street, a sidewalk, a traffic signal, a street light, a sign) or to its parks department (a street tree, a park's facilities, an animal in a park). The column `department` says which. `status` and `closed_at` are as they were on the snapshot date, 2026-10-07: more than a year after the last request was made.

## Why this dataset

The case study needs two organizations whose records share one table, the same days and the same columns, so that a query without the organization visibly mixes them. Two city departments in the same 311 system are exactly that, with real volumes and real gaps. The transport half is the API course's data, so the learner continues an API they know. Compared (details in the authors' `DATASET-RESEARCH.md`): parks (DPR, 48,748 requests in the half year) against environmental protection (DEP, 93,073; more download, no gain) and against splitting the transport data by borough (no download, but boroughs are not separate organizations, and a borough office is not how the city grants access). Parks won: a real second department, a modest size, and the same licence.

## Changes we made

`scripts/build_db.py` applies these rules, and stores them in the table `dataset_info`:

- R1 Keep requests created from 2025-01-01 to 2025-06-30 (New York local time): 110,618 requests.
- R2 Remove repeated submissions: rows that are equal in every column except the ID are one request sent more than once. Keep the lowest ID. (146 removed.)
- R3 Leave out requests whose close time is before their creation time: we cannot correct them with confidence. (557 left out.)
- R4 Keep no address, no free text and no columns that are the same in every row: drop `city`, `address_type`, `due_date`, `resolution_description` and `resolution_action_updated_date`. The agency becomes `department` (R10). (The pulled files have no street address columns.)
- R5 Write times as `2025-03-01T07:00:00`. The source adds `.000` and has no time zone.
- R6 "Unspecified" and empty values become NULL: borough, community board, status, channel (`UNKNOWN`), location type, council district, ZIP code (if not five digits), latitude and longitude.
- R7 Short, fixed codes: borough `STATEN ISLAND` becomes `staten_island`, status `In Progress` becomes `in_progress`, channel `PHONE` becomes `phone`.
- R8 `days_to_close` = `closed_at` − `created_at` in days, rounded to 2 decimals, when `closed_at` is set.
- R9 Every request ID is unique (checked).
- R10 `department` = `transport` for agency DOT and `parks` for agency DPR. R2 and R9 are applied to each department's file; the IDs are unique across both too.

109,915 transport requests and 48,743 parks requests remain. For parks: R2 removed 5 repeated submissions, R3 none; R6 set 8 boroughs, 3 statuses and 7,105 channels to NULL.

The SQL course's case study [Prepare a leak-free table for city repair requests](https://learning.nextia-ai.com/courses/sql/m07/prepare-a-leak-free-table-for-city-repair-requests/) builds a fuller cleaning pipeline on the same frozen file. R1 to R3, R6 and R8 are the core rules of that pipeline, applied here to the first half of 2025. That case study keeps the source values (`STATEN ISLAND`, `Closed`, times with a space). This database normalises them for API clients (R5, R7): lowercase codes, ISO times with `T`, and `council_district` as a number.

## Columns

| Column | Meaning |
|---|---|
| `id` | The city's `unique_key` |
| `created_at`, `closed_at` | When the request was made and closed, New York local time |
| `status` | `open`, `assigned`, `in_progress`, `pending`, `closed`, or NULL |
| `complaint_type`, `descriptor` | What the request is about, for example `Street Condition` / `Pothole` |
| `location_type` | For example `Street`, `Sidewalk`; NULL for 59% of rows (64,666) |
| `borough` | `bronx`, `brooklyn`, `manhattan`, `queens`, `staten_island`, or NULL (598 rows) |
| `community_board`, `council_district`, `incident_zip` | Areas of the city |
| `channel` | `online`, `phone`, `mobile`, `other`, or NULL (65,906 rows were `UNKNOWN`) |
| `latitude`, `longitude` | The place, often an intersection; NULL for 16,647 rows |
| `days_to_close` | Days from creation to closing, when `closed_at` is set (rule R8) |
| `department` | `transport` (DOT) or `parks` (DPR): the organization whose people may see the request in this API |

## Limitations and cautions

- **Requests are not problems.** Several people can report the same pothole. The city closes many requests as duplicates, sometimes at once (4,890 transport requests have `closed_at` equal to `created_at`).
- **Closed is not repaired.** A request can be closed because the inspector found nothing, or because another agency is responsible. The resolution text that says which was removed (R2).
- **Batch times.** 867 transport requests have the time 07:00:00 exactly: Staten Island potholes entered in groups. Do not read them as a peak at 7 a.m.
- **Odd close times.** 557 requests had a close time before their creation time and are left out (R3). 203 requests have a close time but a status other than `closed`. The status is filled in inconsistently, so the API counts a request as closed when `closed_at` is set, as the SQL course's case study does.
- **Who reports.** 311 requests show where people report, not only where the problems are. Areas where fewer people use 311 can look better than they are.
- **Location.** Latitude and longitude point to a street or an intersection, not to a person. No name, phone number or address of a reporter is in the source.

- **Parks snapshot is newer.** The parks file was pulled three days after the transport file. Statuses of the two departments are as of different days (2026-10-07 and 2026-10-10).
- **Two departments, one city.** A sidewalk problem near a tree can be a parks request ("Root/Sewer/Sidewalk Condition") or a transport request ("Sidewalk Condition"). The API keeps each department's requests apart on purpose; a city-wide view needs its own permission, which this API does not have.
