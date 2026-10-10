# Dataset card: Boston 311 Service Requests (2024, 2025, and one week of the new system)

Used by: the case study *Design and tune storage for an open public dataset* (Databases and
Storage for AI Applications, Nextia Learning), `scripts/download.py`, `scripts/load.py`,
`scripts/load_new.py`.

| Field | Value |
|---|---|
| Source | https://data.boston.gov/dataset/311-service-requests (Analyze Boston, the City of Boston's open data portal) |
| Publisher / creator | City of Boston |
| Licence | Open Data Commons Public Domain Dedication and License (PDDL) 1.0, https://opendatacommons.org/licenses/pddl/1-0/ |
| Attribution text | "311 Service Requests, City of Boston (Analyze Boston), PDDL 1.0." (not required by PDDL; we give it anyway) |
| Version or access date | the 2024 and 2025 files as re-published on 2026-09-18 (`lagan_311_open_data_2024_rvsd3.csv`, `..._2025_rvsd3.csv`), downloaded 2026-10-10; the new-system file downloaded 2026-10-10 |
| File used | `boston_311_2024.csv`, `boston_311_2025.csv`: not kept in the project (downloaded by `scripts/download.py`); `data/boston_311_new_system_2026-10-01_07.csv`: kept (PDDL allows it) |
| SHA-256 | 2024: `a3f80f43cc03e00a87fcb26bf2c66bc9ed63dc7ee349b8d3aa803ebac288502d`; 2025: `9924067503d044b376001f3fa3ddfc8d378f321e5da8c761d47e8a863a957a56`; new-system week: `031fc4abc2924853ccc326b2efb0ea84e99741b3fa27bc8ecf0e07b173f152c3` |
| Size | 2024: 306,756 rows × 30 columns, 182 MB; 2025: 276,093 rows × 30 columns, 159 MB; new-system week: 3,540 rows × 28 columns, 1.1 MB |

## What one row means

One service request to the city's 311 system: a person (by phone, the app or the website) or a
city worker reported a problem, such as a pothole, a missed trash pickup or a broken street light.
The row has its times (opened, target, closed), its status, its type and queue, and where it is.
There is no target to predict: the case study is about storage.

## Why this dataset

Real access patterns (a case lookup, crews' work queues, a neighborhood feed, a duplicate check,
reports), a size that makes full scans slow but fits a laptop, a fixed file per year (so a SHA-256
check works), a public domain licence, and real rule breaks to handle. Compared with San Francisco
311 (PDDL, but only a live export), Chicago 311 (unclear terms), NYC 311 (not a standard licence,
used twice in the platform) and Toronto 311 (no licence in its metadata).

## Changes we made

- The load maps the city's values: times as Boston local time (America/New_York); status and
  on-time in lower case; ward "Ward 5"/"05"/"5" as 5; ward 0 and council district 0 as NULL;
  "&amp;" as "&"; empty text as NULL. Columns that no query reads are not loaded (photos, the
  geometry, fire, police and neighborhood-services districts, precinct).
- The new-system week: requests opened 1–7 October 2026 (UTC date), sorted by case ID, with
  `closure_comments`, `submitted_photo` and `closed_photo` emptied (free text and photo links that
  the project does not use).

## Limitations and cautions

- **A snapshot.** Statuses are as the city published them; 120,140 requests of 2024–2025 were still
  open in the file. Some are reopened later.
- **A request is not a problem.** Several people report the same problem; the duplicate check found
  83 of 3,540 new-system requests with the same type open at the same address in the previous 30
  days.
- **Who reports.** 311 shows where people report, not only where problems are. Do not rank
  neighborhoods by request counts as if they measured conditions. City workers created 42% of the
  2024 requests ("Employee Generated").
- **Two systems.** The new system (from August 2025) has other IDs, statuses, categories and
  neighborhood names ("South Boston" and "South Boston / South Boston Waterfront"). Comparisons
  across the change are not like for like.
- **Free text.** Titles and closure reasons are the city's text. They are short, but do not join the
  data with other sources to find out who reported what.
