# Dataset card: Bike Share Toronto ridership, June 2025

Used by: the case study *Plan overnight bike rebalancing*, `C04/M07-L03-plan-overnight-bike-rebalancing/plan-overnight-bike-rebalancing.ipynb` (and `-solution.ipynb`). Numbers: `reference/c04/case-studies/cs03_bikes.py`.

| Field | Value |
|---|---|
| Source | Bike Share Toronto Ridership Data, City of Toronto Open Data: https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/ |
| Publisher / creator | Toronto Parking Authority (owner division), published by the City of Toronto |
| Licence | Open Government Licence – Toronto, version 1.0: https://open.toronto.ca/open-data-licence/ ("Copy, modify, publish, translate, adapt, distribute or otherwise use the Information in any medium, mode or format for any lawful purpose") |
| Attribution text | "Contains information licensed under the Open Government Licence – Toronto." |
| Version or access date | Resource `bikeshare-ridership-2025.zip` (https://opendata.toronto.ca/toronto.parking.authority/bike-share-toronto-ridership-data/bikeshare-ridership-2025.zip, 226,611,421 bytes, SHA-256 `516b1ade12f1551d8b75a42a495885e85130b6c48c85c39d132b907a398e1c62`, resource last modified 2026-10-06), downloaded 2026-10-07. Member `bikeshare_2025_06.csv` (dated 2025-11-13 in the zip, 134,578,131 bytes, SHA-256 `c2ec2b8694c8ba1707a247a999733b690f064a3b039bb590a5be8d6edbfd855e`). |
| File used | `bike_share_toronto_2025-06.csv.gz`, kept in labs `C04/case-studies/data/`: yes (the licence allows redistribution) |
| SHA-256 | `aa77c492b88cefd20117e8303861f8068c4574f99c39a75a9682aa7645d7301e` |
| Size | 980,624 rows × 11 columns; 27.7 MB compressed, 133.6 MB as text |

## What one row means

One rental: a bike taken from one station and returned to a station (or not returned to a known station). The case study builds its own target from the rows: each station's **net outflow from 7:00 to 10:00** on a working day (departures minus arrivals of clean trips), the bikes a station loses in the morning peak.

## Encoding: the hosted copy is UTF-8, the city's file is cp1252

Checked on 2026-10-07, byte for byte: the hosted file is the city's `bikeshare_2025_06.csv` **decoded as cp1252 (Windows-1252), encoded as UTF-8, with CRLF line ends changed to LF**, then compressed with gzip. Decoding the source as cp1252, replacing `\r\n` by `\n` and encoding as UTF-8 gives exactly the hosted text. Nothing else changed: same rows, same order, same columns, same values.

The only characters outside ASCII are in station names: `–` (en dash, 1,858 times, for example `25 York St – Union Station South`) and `É`, `û`, `é` (462 times each, `Lundy Ave / Étienne Brûlé Park`). Read the hosted copy with UTF-8 (the pandas default). Read a fresh download from the city with `encoding="cp1252"`: as UTF-8 it fails with `can't decode byte 0x96`. The UTF-8 copy read as cp1252 shows `â€“` and `Ã‰tienne BrÃ»lÃ©` and does not fail, which is the quiet version of the mistake.

## Columns

| Column | Meaning | Used as |
|---|---|---|
| `Trip_Id` | Trip number, unique (980,624 distinct) | Key, tie-breaker in `LAG` |
| `Trip_Duration` | Seconds; equals `End_Time − Start_Time` within 2 s in every row with an end time | Quality rules |
| `Start_Station_Id`, `Start_Station_Name` | Station where the trip started; exactly one name per ID and one ID per name (916 stations) | Station table, departures |
| `Start_Time` | `YYYY-MM-DD HH:MM:SS`, local time (the peaks are at 8:00 and 17:00), 2025-06-01 00:00:15 to 2025-06-30 23:59:53 | Departures, bike order |
| `End_Station_Id` | Station where the trip ended; empty in 830 rows | Arrivals, van moves |
| `End_Time` | Empty in 130 rows; 193 trips end in July | Arrivals |
| `End_Station_Name` | **Not usable**: equals `Start_Station_Name` in 100% of rows (export defect), although the end ID differs in 937,190 rows | Not used; names come from the start side |
| `Bike_Id` | Bike number (8,874 bikes) | `LAG` per bike |
| `User_Type` | `Member` 662,498, `Casual` 318,126 | Not used |
| `Bike_Model` | `ICONIC`, `EFIT`, `EFIT G5` | Not used |

## Why this dataset

The brief asked for real trips with a permissive licence and visible data-preparation problems. Citi Bike was rejected (its licence forbids hosting the data); Oslo Bysykkel (NLOD 2.0) and Helsinki/Espoo city bikes (CC BY 4.0) were compared (`research/out_bike_oslo_helsinki.txt`). Toronto won because its file has the problems the course teaches, all real: a cp1252 source file, a broken end-name column, trips without an end, zero-second trips, false starts, and bikes that change station with no trip (van moves, found with `LAG`). One month is large enough to be realistic (980,624 trips) and small enough for a free Colab session (about 10 s to load into SQLite).

## Changes we made

Encoding and line ends only (see above). The case study itself does not change the file; it quarantines rows in SQL:

| Rule (in this order) | Trips |
|---|---|
| `no_end_time` | 130 |
| `no_end_station` | 724 |
| `over_24_hours` | 2 |
| `false_start` (same station, under 120 s) | 3,665 |
| `under_60_seconds` (to another station) | 1,233 |
| clean | 974,870 |

## Known traps and limits

- `End_Station_Name` is a copy of the start name in every row. Take end names from the start side (`stations` table). Four end IDs (7638, 7690, 7793, 8065; 10 trips) never appear as a start, so they have no name.
- 830 trips have no end station and 130 no end time (106 both). Many of them end at a whole minute (`…:00`), unlike normal trips: probably closed by the system, not by a dock.
- 779 trips last 0 seconds; 2,426 under 60 s; 5 over 24 hours (all about 24 h 0–30 min).
- 43 trips start before the same bike's previous trip ended (clock or record errors).
- 60,554 trips (6.2%) start at a station other than where the same bike's previous trip ended: a move with no rider trip (rebalancing vans, repairs, or missing records; the file cannot tell which). 689 more follow a trip with no end station.
- The file is selected by **start** time: trips that started on 31 May and ended on 1 June are missing, so arrivals early on 1 June are slightly low (a Sunday; not a target day).
- Departures show used bikes, not demand: a rider who finds an empty station leaves no row. There is no dock status (bikes available) and no station capacity in this data.
- June 2025 has no public holiday in Ontario; 1 July (Canada Day) is outside the file.
- Times are local; the file has no time-zone column.

No personal data: no names, no card or account numbers. `User_Type` is the only fact about a rider.
