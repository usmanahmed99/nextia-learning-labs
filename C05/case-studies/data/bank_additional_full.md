# Dataset card: bank_additional_full.csv.gz

Used by the case study *Rank a call list* in the machine learning course (labs `C05/M09-L04-rank-a-call-list/`).

| | |
|---|---|
| **Source** | UCI Machine Learning Repository, *Bank Marketing*, https://archive.ics.uci.edu/dataset/222/bank+marketing (file `bank-additional/bank-additional-full.csv` inside `bank-additional.zip`) |
| **DOI** | 10.24432/C5K306 |
| **Creators** | Sérgio Moro, Paulo Rita, Paulo Cortez |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the UCI page (checked 2026-10-07) |
| **Accessed** | 2026-10-07 |
| **Hosted file** | labs `C05/case-studies/data/bank_additional_full.csv.gz` (gzip CSV, 0.34 MB) |
| **SHA-256** | `baad13c38bee0bff5279e68e1f32a8dc60084c2fb05600cd40a5a2ea4d2ce850` |
| **Rows, columns** | 41,188 rows, 21 columns |
| **One row** | The last phone contact with one client in one direct-marketing campaign of a Portuguese bank, May 2008 to November 2010, with facts about the client, the call, earlier campaigns and the economy at that time. |
| **Target** | `y`: did the client subscribe a term deposit? `yes` for 4,640 rows (11.3%). |

## Attribution text (required by CC BY 4.0)

> Data: "Bank Marketing" by S. Moro, P. Rita and P. Cortez, UCI Machine Learning Repository, https://doi.org/10.24432/C5K306, licensed under CC BY 4.0. Changed by Nextia Learning: the file bank-additional-full.csv saved with commas instead of semicolons and gzip-compressed (see the card).

## Citation

- Moro, S., Rita, P., & Cortez, P. (2014). *Bank Marketing* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5K306
- Moro, S., Cortez, P., & Rita, P. (2014). A data-driven approach to predict the success of bank telemarketing. *Decision Support Systems*, 62, 22–31. https://doi.org/10.1016/j.dss.2014.03.001

## Exact changes made to the source file

1. Read `bank-additional-full.csv` with `;` as the separator.
2. Wrote all 41,188 rows and 21 columns, unchanged in value and order, as UTF-8 CSV with `,` as the separator and no index, gzip-compressed with `mtime=0`. Script: `nextia-learning/reference/c05/case-studies/research/make_hosted.py`.

The rows keep the source order, which is time order (the source says "ordered by date"). The case study depends on that order.

## Columns used in the case study

| Column | Meaning | Use |
|---|---|---|
| `age` | Age of the client | Input (also used for a slice check) |
| `job`, `marital`, `education` | Type of job, marital status ("divorced" includes widowed), education | Inputs (categories; "unknown" kept as a category) |
| `default`, `housing`, `loan` | Has credit in default? A housing loan? A personal loan? (yes, no, unknown) | Inputs (categories) |
| `contact` | cellular or telephone | Input |
| `month`, `day_of_week` | Month and weekday of the last contact | Inputs |
| `duration` | Length of the last call, in seconds | **Leak: known only after the call. Never an input; shown only to explain the leak.** |
| `campaign` | Contacts with this client in this campaign, including the last one | Input (see the traps) |
| `pdays` | Days since the client was last contacted in an earlier campaign; 999 = never | Replaced by `contacted_before` (1 if `pdays` is not 999) |
| `previous`, `poutcome` | Contacts before this campaign; outcome of the earlier campaign (failure, nonexistent, success) | Inputs |
| `emp.var.rate`, `cons.price.idx`, `cons.conf.idx`, `euribor3m`, `nr.employed` | Employment variation rate (quarterly), consumer price index and consumer confidence index (monthly), 3-month Euribor rate (daily), number of employees (quarterly): Portuguese national indicators | Inputs (see the traps) |
| `y` | Target, see above; the notebook makes a 0/1 column `subscribed` | Target |

## Known traps

- **The `duration` leak.** The source itself warns that `duration` "is not known before a call is performed" and should be discarded for a realistic model. With it, a tree reaches ROC AUC 0.94 on validation; without it, 0.76 to 0.80.
- **"unknown" values.** `default` 8,597, `education` 1,731, `housing` and `loan` 990 each, `job` 330, `marital` 80. They are missing answers, coded as a label. `default = yes` occurs only 3 times, so that column says almost nothing apart from "unknown".
- **A code inside a number.** `pdays = 999` (96.3% of rows) means "never contacted"; a linear model would read it as 999 days.
- **`campaign` includes the last contact.** It counts calls until the end of the campaign for this client. Before the first call of a campaign it is not known; the case study treats it as "calls so far" and says so.
- **Time order and drift.** The yes rate rises from 2.8% in the first tenth of the file to 46.0% in the last tenth, while the Euribor rate falls from about 4.9 to 0.8. The five economic indicators act as clocks: a random split mixes periods, a time split shows the drift.
- **No client ID.** A client can appear in several campaigns; the data does not let you keep a client's rows together.
- **12 exact repeats.** The case study drops them (41,176 rows remain).
- **Privacy.** The source left out some attributes for privacy reasons. Age, job and marital status are personal data; the case study uses them as the original study did and checks who ends up on the call list by age.
