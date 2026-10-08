# Dataset card: Bike Sharing (hourly), Washington, D.C., 2011–2012

Used by: the case study *Forecast bike-share demand* in the machine learning course, `C05/M09-L01-forecast-bike-share-demand/forecast-bike-share-demand.ipynb`

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, dataset 275: https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset |
| DOI | 10.24432/C5W894 (https://doi.org/10.24432/C5W894) |
| Publisher / creator | Hadi Fanaee-T, LIAAD, University of Porto / INESC Porto. Rentals from the Capital Bikeshare system (system data, http://capitalbikeshare.com/system-data); weather from freemeteo.com; holidays from the D.C. Department of Human Resources. |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/ — stated on the UCI page (checked 2026-10-07). The file's Readme also asks publications to cite the paper below. |
| Attribution text | Fanaee-T, H. (2013). *Bike Sharing* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5W894. Licensed under CC BY 4.0. Hosted unchanged (gzip) by Nextia Learning. |
| Citation | Fanaee-T, H. and Gama, J. (2013). Event labeling combining ensemble detectors and background knowledge. *Progress in Artificial Intelligence*, Springer. doi:10.1007/s13748-013-0040-3 |
| Version or access date | UCI page last updated 2024-03-10; downloaded 2026-10-07 |
| File used | `bike_sharing_hour.csv.gz` (labs `C05/case-studies/data/`) = `hour.csv` from the UCI zip, gzip-compressed (mtime 0) |
| SHA-256 | `c5ef0c31d5ee006449eaf72f3c2071c68891e82f1f8597074304063e57f1353d` |
| Size | 17,379 rows × 17 columns, 0.26 MB compressed |

## What one row means

One hour of the whole bike-share system: the number of bikes rented in that hour (`cnt`, the target), with the calendar and the weather of that hour.

## Why this dataset

Real hourly demand with a strong daily shape that differs between working days and other days, a clear weather effect, strong growth between the two years (+63% in mean rentals per hour), a built-in leak (`casual` + `registered` = `cnt`) and real events (Hurricane Sandy, 29–30 October 2012). It shows why a time split, count-aware losses and error slices matter. Alternatives considered in the research (`research/f1_bike.py`): the daily file of the same dataset (731 rows: too small for hourly planning) and synthetic counts (no real events).

## Changes we made

None. The CSV is byte-for-byte `hour.csv`, compressed with gzip (`make_hosted.py`). In the case study, the notebook adds columns on the fly (`day_type`, `hour_type`, past rentals) and never writes the data file.

## Columns used

| Column | Meaning |
|---|---|
| `dteday` | date (2011-01-01 to 2012-12-31) |
| `hr` | hour, 0–23 |
| `weekday` | day of the week, 0 = Sunday |
| `workingday` | 1 if neither weekend nor holiday |
| `holiday` | 1 on a public holiday |
| `mnth` | month, 1–12 |
| `yr` | 0 = 2011, 1 = 2012 |
| `weathersit` | 1 clear or partly cloudy; 2 mist or cloudy; 3 light rain or snow; 4 heavy rain, ice or snow |
| `temp`, `atemp` | temperature and "feels like" temperature, divided by 41 and 50 (°C) |
| `hum` | humidity, divided by 100 |
| `windspeed` | wind speed, divided by 67 |
| `cnt` | target: rentals in the hour |
| `casual`, `registered` | rentals by casual and registered users: **leak** (they add up to `cnt`), used only to show the leak |

Not used: `instant` (row number), `season` (the same information as `mnth`).

## Known traps

- **Leak:** `casual + registered == cnt` in every row; both are counted in the same hour.
- **Missing hours:** 165 hours have no row (115 in 2011, 50 in 2012); 23 on 2012-10-29 and 13 on 2012-10-30 (Hurricane Sandy, system closed). A row count per day is not always 24.
- **Odd values:** `hum == 0` in 22 rows (sensor gaps); `windspeed == 0` in 2,180 rows (probably "not measured"); `weathersit == 4` in only 3 rows.
- **Weather is observed, not forecast:** a real forecast the evening before would use the weather forecast, which is less accurate. Results are optimistic.
- **Growth:** the system grew 63% from 2011 to 2012; a random split hides it, a time split shows it.
- **System level only:** no station-level counts, so the data cannot plan the rebalancing of single stations.
