# Dataset card: Diabetes 130-US hospitals, 1999–2008

Used by C05-M09-L05 *Choose a model for hospital readmissions* (case study). The lead copies this card to labs `C05/case-studies/data/diabetes_130_hospitals.md`.

| | |
|---|---|
| **Files** | `diabetes_130_hospitals.csv.gz` (gzip CSV, 3.00 MB, 101,766 rows × 50 columns) and `IDS_mapping.csv` (2.5 KB, the code tables) |
| **SHA-256** | `diabetes_130_hospitals.csv.gz`: `7e2cd49bd158b99bef449897d3f5118881dc469115c6e80189fd248355b08eac`<br />`IDS_mapping.csv`: `f1bb82b471cb34649352597572c9b1fb00bd27f77b9f5a22a03dc3eb1039749e` |
| **Source** | UCI Machine Learning Repository, dataset 296, *Diabetes 130-US Hospitals for Years 1999-2008*: <https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008> |
| **DOI** | [10.24432/C5230J](https://doi.org/10.24432/C5230J) |
| **Creators** | John Clore, Krzysztof Cios, Jon DeShazo, Beata Strack (donated 2014-05-02) |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0), as stated on the UCI page (checked 2026-10-07) |
| **Accessed** | 2026-10-07 |

## Attribution (required by CC BY 4.0)

> Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). *Diabetes 130-US Hospitals for Years 1999-2008* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5230J. Licensed under CC BY 4.0. Changed by Nextia Learning: see "Changes" below.

**Paper to cite** (the study that describes the data):

> Strack, B., DeShazo, J. P., Gennings, C., Olmo, J. L., Ventura, S., Cios, K. J., & Clore, J. N. (2014). Impact of HbA1c measurement on hospital readmission rates: analysis of 70,000 clinical database patient records. *BioMed Research International*, 2014, 781670. https://doi.org/10.1155/2014/781670

## What one row means

One row is one **hospital encounter** (a stay of 1 to 14 days) of a patient with diabetes, in one of 130 US hospitals between 1999 and 2008. The source selected encounters where diabetes was entered as a diagnosis, laboratory tests were done and medication was given. `encounter_id` is unique; `patient_nbr` identifies the patient, and 16,773 of the 71,518 patients have more than one encounter. The target column `readmitted` says whether the patient came back as an inpatient within 30 days (`<30`), after more than 30 days (`>30`), or not in the records (`NO`).

## Changes made by Nextia Learning (exact)

1. The file was read with pandas 3.0.6 (`dtype=str`, default missing-value markers) from the UCI `diabetic_data.csv` and written back as CSV with gzip (`mtime=0`). The rows, the columns and their order are unchanged.
2. **One side effect, kept on purpose and documented here:** pandas reads the text `None` as missing, so in the columns `max_glu_serum` (96,420 rows) and `A1Cresult` (84,748 rows) the source value `None` is an **empty cell** in this copy. In the source, `None` means "the test was not done". Read an empty cell in these two columns as "not measured". No other cell differs from the source (checked cell by cell on 2026-10-07).
3. The source's missing marker `?` is kept as it is.
4. `IDS_mapping.csv` is the UCI file, byte for byte.

The case study then makes its own changes in the notebook (they are not in the hosted file): it removes the 2,423 encounters that ended in death or a hospice discharge (discharge codes 11, 13, 14, 19, 20, 21), translates the three code columns with `IDS_mapping.csv`, groups the main diagnosis into nine groups (as in Strack et al. 2014), and turns the age band into a number.

## Columns the case study uses

| Column | Meaning (plain words) | Use |
|---|---|---|
| `encounter_id` | The stay's number | Check that rows are unique |
| `patient_nbr` | The patient's number | **Split by patient**; never an input |
| `readmitted` | `<30`, `>30` or `NO` | Target: `<30` → 1, else 0 |
| `age` | 10-year band, `[0-10)` to `[90-100)` | Input (as the middle of the band) and slices |
| `admission_type_id`, `admission_source_id`, `discharge_disposition_id` | Codes for how the patient came in and where they went; text in `IDS_mapping.csv` | Inputs (as text); discharge codes also remove deaths and hospice |
| `time_in_hospital` | Days in hospital | Input |
| `num_lab_procedures`, `num_procedures`, `num_medications`, `number_diagnoses` | Counts during the stay | Inputs |
| `number_outpatient`, `number_emergency`, `number_inpatient` | Visits of the patient in the year before the stay | Inputs |
| `medical_specialty` | Specialty of the admitting doctor (49% missing) | Input; missing is its own value |
| `diag_1` | Main diagnosis, ICD-9 code | Input as one of nine groups |
| `A1Cresult`, `max_glu_serum` | HbA1c and blood glucose test results; empty = not measured | Inputs |
| `insulin`, `change`, `diabetesMed` | Insulin dose change, any diabetes medication change, any diabetes medication | Inputs |
| `race`, `gender`, `payer_code` | Sensitive (see below) | **Slices only, never inputs** |

Not used: `weight` (97% missing), `diag_2`, `diag_3` and the 22 other medication columns (to keep the case study small).

## Known traps

- **`?` means missing**; read with `na_values="?"`. In this copy, an empty `A1Cresult` or `max_glu_serum` means "not measured" (see Changes).
- **Several codes mean "unknown"**: `NULL`, `Not Available`, `Not Mapped`, `Unknown/Invalid` in `IDS_mapping.csv`.
- **`IDS_mapping.csv` holds three tables** one after the other, separated by an empty line; some descriptions start with a space.
- **Deaths and hospice discharges** cannot be readmitted; keep them out of a readmission model.
- **Repeat patients**: 46% of rows belong to patients with more than one encounter. A random split by row puts the same patient in train and test.
- **No dates**: the file has no admission dates, so a split by time is not possible. `encounter_id` grows roughly with time, but the source does not document it.
- **Counting a patient's encounters in the whole file** uses later encounters, which are not known at discharge (a leak).
- **Old data**: 1999–2008, US hospitals. Care, coding (ICD-9, not ICD-10) and payers have changed since.
- **Weak signal**: readmission depends on many things that are not in the file (support at home, follow-up care). In the case study, the best of four model families reaches a ROC AUC of only about 0.67 on unseen patients.

## Sensitivity

The data is de-identified by the source, has no names or dates, and is published for research under CC BY 4.0. It is still health data about real people: do not try to re-identify anyone. `race`, `gender` and `payer_code` (the type of insurance, a sign of income) are sensitive. The case study keeps them out of the model's inputs and uses them only to check whether the model works equally well for each group. `payer_code`'s codes are not explained in the source; the paper names examples such as Medicare and self-pay.

## Why this dataset

It is real, openly licensed, large enough (≈100,000 rows) to compare four model families with cross-validation, and small enough (3 MB) for a free notebook. It has the problems a real readmission project has: codes, missing values, repeat patients, sensitive columns and a weak signal. Alternative considered: MIMIC-IV (much richer, but needs credentialed access and a data-use agreement, so it cannot be redistributed).
