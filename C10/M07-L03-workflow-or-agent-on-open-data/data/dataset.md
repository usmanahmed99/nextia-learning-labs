# Dataset card: San Diego "Get It Done" requests, a fixed sample

Used by: the case study *Workflow or agent? Automate an open-data process* (AI Agents and Workflow Orchestration), `workflow-or-agent-on-open-data.ipynb`

| Field | Value |
|---|---|
| Source | City of San Diego Open Data Portal, "Get It Done Reports": https://data.sandiego.gov/datasets/get-it-done-311/ (files `get_it_done_requests_closed_2025_datasd.csv` and `get_it_done_requests_closed_2026_datasd.csv`) |
| Publisher / creator | City of San Diego |
| Licence | Open Data Commons Public Domain Dedication and Licence (PDDL) 1.0, https://opendatacommons.org/licenses/pddl/1-0/ (the dataset page links https://opendefinition.org/licenses/odc-pddl/). Portal terms: https://data.sandiego.gov/help/guides/terms/ ("as is", no warranty) |
| Attribution text | Data: City of San Diego, "Get It Done Reports", https://data.sandiego.gov/datasets/get-it-done-311/, public domain (ODC PDDL). Sample, redaction and changes by Nextia Learning. (The PDDL asks for no attribution; we give it anyway.) |
| Version or access date | Downloaded 2026-10-09 21:18 UTC. Source files: closed 2025, SHA-256 `52cfa8d4fd3704d84cadc9203ed9054f51a10e217bf710a405fd1f6734ced231`; closed 2026, SHA-256 `c925ea1ff074c1a74bf5bc2dbdb6c79fdbb31246b06c6be32b8f806c987f9a57`. The city replaces the files every day. |
| Files used | `data/dev.jsonl`, `data/test.jsonl`, `data/pool.jsonl`, `data/catalogue.csv`, `data/period_mix.json`, kept in this folder: yes (public domain). Checksums in `SHA256SUMS`. |
| Size | dev 150, test 300, pool 1,500 requests (7 fields each); catalogue 281 rows × 4; about 0.4 MB |

## What one row means

One request that a resident sent through the city's Get It Done app or website, and the city closed. `text` is the resident's description (redacted). `group` is the **City staff group that the city's system recorded for the request** (`case_record_type`, renamed to a short path name): the outcome that every design must predict. `service_name` and `service_detail` are the service type recorded for the request; no design sees them (they would give the answer away), and the analysis uses them only to read the errors.

The nine groups, with the city's own name in brackets: `parking` (Parking), `environmental_services` (ESD Complaint/Report), `streets` (TSW), `neighborhood_policing` (Neighborhood Policing), `right_of_way_enforcement` (TSW ROW), `parks` (Parks & Recreation), `development_services` (DSD), `traffic_engineering` (Traffic Engineering), `storm_water_enforcement` (Storm Water Code Enforcement).

## Why this dataset

It has the resident's own words *and* the process's own outcome, for a real public process with nine teams. Two years let us write the rules on 2025 and test them on 2026. Compared with New York City's 311 data (no resident text; the agency follows from the complaint type) and Boston's 311 data (no resident text; a new system from October 2025). Details: `reference/c10/m07/l03/DATASET-RESEARCH.md` in the course repository.

## Changes we made

Script: `build_sample.py` (seed 10).

1. Kept requests sent by residents through the app or the website (`case_origin` Mobile or Web), with a description, status Closed, not marked as a duplicate of another request (`service_request_parent_id` empty), and handled by one of the nine groups (99.99% of these rows).
2. Text: repaired double-encoded characters; removed the web form's "|| LOCATION: …" tail; replaced e-mail addresses with `[email]`, phone numbers with `[phone]`, codes that mix letters and digits (licence plates, permit numbers) with `[plate]`, links with `[link]`, and every number of 3 or more digits (house numbers, ZIP codes, listing numbers) with `[number]`; dropped texts longer than 400 characters, texts with profanity, and texts that give a person's name ("my name is", "his name is").
3. Samples: **dev**, 150 requests created 2025-01-01 to 2025-06-30; **test**, 300 requests created 2026-01-01 to 2026-10-08. Each is stratified by group: every small group gets at least 8 (dev) or 12 (test) requests, the rest follow the period's mix. So the samples over-represent small groups; `period_mix.json` has the real mix to weight results back. **pool**: 1,500 other 2025 requests (same rules) that the agent's `similar_requests` tool searches. **catalogue**: every service type and detail of the 2025 period with its group and number of requests (`search_services` reads it).
4. A privacy review: the course author read every dev and test text; a text that names or could identify a private person, or describes children or a medical situation in detail, was excluded, and the next request of the same group took its place (IDs in `privacy_excluded.txt` in the course repository). The 1,500 pool texts passed the automatic rules only. A later scan found the names of people in 8 pool texts and a house number joined to a word in one more: all 9 were replaced with `[name]` or `[number]`, and the 4 recorded agent requests that had read 3 of them were recorded again.
5. 40 requests of 2026 that we printed while choosing the dataset are never in a sample.
6. Dates: only the creation date (no time). Dropped every other column (address, coordinates, district, park name and the rest).

## Limitations and cautions

- **The outcome is the city's record, not a judgement.** In the app, the resident first picks a service type, and the group mostly follows from that choice; city staff may change it. We cannot tell which happened. So "right" means "agrees with where the city's system sent and closed the request". A resident who picked the wrong type, and staff who did not correct it, give a wrong outcome that every design is scored against.
- **The text was written after the category was chosen**, so many descriptions are short ("Graffiti", "Daylighting"). A design sees only the text, so it has less information than the city had. Messages in a channel without categories (e-mail, chat) would be longer.
- **Referred requests are not here** (sent to Caltrans, SDG&E and others: about 7% of closed requests in 2025). A real router must also recognise them.
- **Encampments** go to Neighborhood Policing or to Environmental Services; **graffiti** to Streets or to Right-of-Way Code Enforcement. The rule that decides (for example, whose property) is not in the text, so some disagreement is expected from any design.
- The redaction is automatic and can miss things or remove useful words ("[number] feet"). Descriptions describe people in public spaces, including people without homes: use them to study routing, not to study people.
- A sample of 300 gives intervals of about ±5 percentage points on one share. Small groups have 12 requests each: their numbers are examples, not estimates.
