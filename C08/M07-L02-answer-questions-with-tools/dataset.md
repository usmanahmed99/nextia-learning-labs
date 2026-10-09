# Dataset card: World Development Indicators, 8 countries × 6 indicators, 2000–2025 (snapshot of 2026-10-08)

Used by: the case study *Answer questions with tools over open data* (Building Reliable Applications with LLM APIs), project `stats-assistant`

| Field | Value |
|---|---|
| Source | [World Development Indicators](https://datacatalog.worldbank.org/search/dataset/0037712/World-Development-Indicators), read through the World Bank Indicators API (`https://api.worldbank.org/v2/`, source 2) |
| Publisher / creator | The World Bank, with its data providers (see "Data providers" below) |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), under the World Bank's [dataset terms of use](https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets) (they add a mediation and arbitration clause). The API metadata of each of the 6 series says `License_Type: CC BY-4.0`. |
| Attribution text | The World Bank: World Development Indicators: data providers as listed below. Adapted (reshaped) by Nextia Learning. |
| Version or access date | Downloaded 2026-10-09 03:24 UTC (2026-10-08 evening, Toronto). The API reported `lastupdated: 2026-10-08` for every series. |
| File used | `wdi_snapshot.csv`, `countries.csv`, `indicators.csv`, kept in `data/`: yes (CC BY 4.0 allows redistribution with attribution) |
| SHA-256 | `wdi_snapshot.csv` `259a6b4d4d9257add26efa703747584baff6018b43fc114fcfdc33eecfcb8c99`; `countries.csv` `1025ddba0222a0ae293fd060e8d24c3874855cce6887b930effe0d7cfc04e6f1`; `indicators.csv` `bd7792417e5d95b1cb281df9b5598805a3a5538a37cadbeb47ca21b895a197b7` (also in `data/SHA256SUMS`) |
| Size | `wdi_snapshot.csv`: 1,248 rows × 4 columns, 44 KB |

## What one row means

One value of one indicator for one country in one year, for example `CAN,SP.POP.TOTL,2024,41262329`: Canada's total population in 2024 was 41,262,329. An empty `value` means that the World Bank has no value for that year (23 of 1,248 values).

Countries: Brazil (BRA), Canada (CAN), United Kingdom (GBR), India (IND), Japan (JPN), Mexico (MEX), Nigeria (NGA), United States (USA). Years: 2000 to 2025.

| Indicator code | Name | Data providers (from the World Bank's metadata) |
|---|---|---|
| SP.POP.TOTL | Population, total | UN Population Division, World Population Prospects; national statistical offices |
| NY.GDP.MKTP.CD | GDP (current US$) | National statistical organisations and/or central banks; OECD national accounts; World Bank staff estimates |
| NY.GDP.PCAP.CD | GDP per capita (current US$) | As GDP |
| SP.DYN.LE00.IN | Life expectancy at birth, total (years) | UN Population Division, World Population Prospects; national statistical offices |
| EG.ELC.ACCS.ZS | Access to electricity (% of population) | World Bank, SDG 7.1.1 Electrification Dataset (ESMAP, Tracking SDG7) |
| IT.NET.USER.ZS | Individuals using the Internet (% of population) | International Telecommunication Union (ITU), World Telecommunication/ICT Indicators Database |

## Why this dataset

People ask questions about these numbers every day ("How many people live in Canada?", "Which country has the highest life expectancy?"), and each answer has a country, an indicator and a year: exactly what a tool with checked arguments needs. The licence is clear (CC BY 4.0) and the source is stable and versioned by date. Statistics Canada's tables (Statistics Canada Open Licence) were the other candidate; see `DATASET-RESEARCH.md` in the course's reference files.

## Changes we made

- Kept 8 countries, 6 indicators and the years 2000 to 2025, from the API's JSON.
- Reshaped to one CSV row per (country, indicator, year), sorted. Every value is kept exactly as the API gave it; `null` became an empty cell.
- Added `countries.csv` (code and the API's country name) and `indicators.csv` (code, the API's indicator name, and a unit in words that we wrote).

## Limitations and cautions

- **A snapshot.** The World Bank revises past values when its sources revise them. A number here can differ from today's number on data.worldbank.org. Always state the snapshot date.
- **The latest years are often estimates or missing.** 2025 has values for population, GDP and GDP per capita, but not for life expectancy, electricity, or most Internet values.
- **Current US dollars move with exchange rates.** Nigeria's GDP in current US$ fell 48.24% from 2023 to 2024, largely because the naira lost value against the dollar, not because the economy halved.
- **Modelled and survey-based values.** Life expectancy and population come from UN models; Internet use comes from surveys and estimates, and some years are rounded (75.0, 74.0, 71.0 for the United States in 2007 to 2009).
- **Eight countries are not the world.** "The highest" in an answer means "the highest of these eight".
- Do not present an assistant's text as the official figure: the official figure is the World Bank's, with its date.
