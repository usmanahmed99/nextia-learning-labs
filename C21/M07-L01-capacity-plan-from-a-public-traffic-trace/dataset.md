# Dataset card: San Francisco 311 Cases, arrival times (2025 and June 2026)

Used by: Scaling APIs and AI Workloads, case study *Capacity plan from a public traffic trace*, `capacity-plan-from-a-public-traffic-trace.ipynb` and `replay_trace.py`

| Field | Value |
|---|---|
| Source | https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6 (DataSF, dataset `vw6y-z8j6`, "311 Cases") |
| Publisher / creator | City and County of San Francisco (311 Customer Service Center), published on DataSF |
| Licence | Open Data Commons Public Domain Dedication and License (PDDL) 1.0, https://opendatacommons.org/licenses/pddl/1-0/ |
| Attribution text | "311 Cases", City and County of San Francisco, DataSF (data.sfgov.org), ODC PDDL 1.0. Extract by Nextia Learning. (PDDL does not require attribution; we give it anyway.) |
| Version or access date | Downloaded through the DataSF API (Socrata) on 2026-10-10. The live dataset changes every day, so these files are a fixed copy. |
| File used | `sf311_2025_arrivals.csv.gz` and `sf311_2026_06_arrivals.csv.gz`, kept in this folder: yes (PDDL allows it) |
| SHA-256 | `sf311_2025_arrivals.csv.gz` 57c4209ce8aefb694a99436faef07d3eb6256e1004724fc5ec358ccdc720e548 · `sf311_2026_06_arrivals.csv.gz` 3ea66ddeb5f9ad1cf412dce8253410a0b98958f49337941e305fb30851c599fc |
| Size | 2025: 872,427 rows × 3 columns, 4.0 MB gzip · June 2026: 73,762 rows × 3 columns, 0.34 MB gzip |

## What one row means

One request to San Francisco's 311 service (a pothole, graffiti, a blocked sidewalk, …): `requested_datetime`, when the city's system recorded it, in local time (America/Los_Angeles, no offset), to the second; `source`, the channel (`Phone`, `Mobile`, `Web`, `Integrated Agency`, `Twitter`, `Email`, `Test`, or empty); `service_name`, the request type. There is no target: the case study uses the times as arrivals of AI jobs.

## Why this dataset

It is a real arrival trace of the same kind as the course's help-desk tickets (one request = one ticket = one AI job), about 2,400 a day, with real daily and weekly shapes and real bursts. It has a public-domain licence and no personal data in the three columns we keep. Compared with: Boston 311 (same licence, a third of the volume, and the 2025 change of system splits the year across two files with different columns); the NASA-HTTP web server log of 1995 (no named licence and a use restriction, client host names in every line, web hits are not tickets); New York 311 (terms of use rather than a named licence; used by the course's other case study).

## Changes we made

From the API answer (columns `service_request_id, requested_datetime, source, service_name`, filtered by time): we dropped the request ID (checked unique), cut the milliseconds (always `.000`), sorted the rows, and wrote a gzip without a timestamp so the checksum is stable. Nothing was removed: the 512 `Test` rows and the 1,985 rows without a source stay (the case study's checks find them). June 2026 is the new input at the end of the case study.

## Limitations and cautions

- The time is when the city's system recorded the request, not when the resident sent it. About a third of web requests are recorded in once-a-minute batches (second 47 of the minute in 2025, second 53 in June 2026).
- Local time without an offset: the spring clock change leaves an hour without rows (2025-03-09, 02:00); the autumn change puts two hours into one (2025-11-02, 01:00).
- One city, one year and one month. Do not use the numbers as another city's traffic.
- The full dataset has addresses, coordinates and descriptions. Do not join this extract back to it to study individual residents.
