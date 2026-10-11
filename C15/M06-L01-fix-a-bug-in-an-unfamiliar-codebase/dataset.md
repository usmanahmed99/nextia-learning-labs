# Project card: delivery-slots

Used by: the case study [Fix a bug in an unfamiliar codebase](https://learning.nextia-ai.com/courses/ai-assisted-dev/m06/fix-a-bug-in-an-unfamiliar-codebase/), `starter.zip` and `finished.zip`

| Field | Value |
|---|---|
| Source | Written for this course by Nextia Learning. Not taken from any real system or open-source project. |
| Publisher / creator | Nextia Learning |
| Licence | [MIT](https://opensource.org/license/mit) ("Copyright (c) Nextia Learning"; the text is in `LICENSE` in the project) |
| Attribution text | Keep the `LICENSE` file when you copy the project. "delivery-slots, Nextia Learning" is welcome. |
| Version or access date | 1.0 (the starter's last commit is `ed951ba`) |
| Files used | `starter.zip` and `finished.zip`, kept in this folder: yes |
| SHA-256 | the data files of the starter: `data/zones.csv` `713bb67544135257dc69d89b2f5781823297972b2ae77f7efc48e8fc6e28e686`, `data/slot-plan.csv` `e12390d4b13fd94addd33ea2d6958a503d72bdf55465e5cb177b266649badfe6`, `data/bookings.csv` `ae33de377c3412c4f91d13c4d84c9dc7d2c26d08b8664d6ca10df20b1dbcc064`; the zips: see `SHA256SUMS` |
| Size | 9 Python files (402 lines) and 7 test files (317 lines); 6 commits; 3 CSV files (15 districts, 7 slot rows, 14 bookings) |

## What the project is

`delivery-slots` is a small command-line program of Larkfield's delivery team. It lists the delivery time slots of a postcode on a day, books a slot for an order (with a capacity per slot and a cut-off at 20:00 the day before), and prints a driver's list. It needs only Python's standard library; the tests use pytest.

One row of `data/zones.csv` is a postcode district and its delivery zone. One row of `data/slot-plan.csv` is a slot in a normal week. One row of `data/bookings.csv` is a booked delivery.

## Why this project

The case study needs a codebase that the learner has never seen, small enough to read in an evening, with a real-looking history, an issue written by customer support, and a bug that shows in one place (the slots of a customer) while its cause is in another (the zone lookup, changed by an earlier fix). The course team first chose a real bug in a real open-source library (MIT). Running downloaded third-party code was not allowed on the authoring computer, so the team wrote this project instead. The comparison of the candidates is in the case study's research notes.

## What is constructed

Everything in the project is written for the course: the code, the tests, the Git history and its authors, the issues, Larkfield, its people (Hana, Luis, Grace, Amira), the customer Ruth and the bookings. The postcode districts (LS1 to LS17) are real districts of Leeds; their zones are invented. **The maintainers' fix** (branch `hana/issue-12` in `finished.zip`) is also constructed: the course team wrote it as the delivery team's own fix, so that you have a second, independent fix to compare with yours.

**Real:** the assistant session in `assistant-session/` (Aider 0.86.2 with a hosted model; the exact prompts, replies and the change). The fix on `main` in `finished.zip` is the assistant's change, unchanged, plus two tests that Amira added after her review.

## Changes we made

None after the build. The zips are made by the course's build script from the files of each commit, with fixed authors and dates, so every build has the same commit hashes.

## Limitations and cautions

The project is a teaching example, not a delivery system. It treats every UK postcode as "district + three characters" and does not check the format (the case study shows what that means). It uses local times without a time zone, on purpose. Do not use it for real deliveries.
