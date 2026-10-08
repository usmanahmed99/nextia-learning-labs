# Dataset card: Diabetes 130-US hospitals, for C17-M06-L03 *Score hospital readmissions asynchronously*

Used by: C17-M06-L03 *Score hospital readmissions asynchronously* (`starter.zip`, `finished.zip` in this folder). The full card of the data is [C05/case-studies/data/diabetes_130_hospitals.md](../../C05/case-studies/data/diabetes_130_hospitals.md); this card says how this case study uses it.

| Field | Value |
|---|---|
| Source | UCI Machine Learning Repository, dataset 296, *Diabetes 130-US Hospitals for Years 1999-2008*: https://archive.ics.uci.edu/dataset/296/diabetes+130-us+hospitals+for+years+1999-2008 (DOI [10.24432/C5230J](https://doi.org/10.24432/C5230J)) |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/, as stated on the UCI page (checked 2026-10-07) |
| Attribution | Clore, J., Cios, K., DeShazo, J., & Strack, B. (2014). *Diabetes 130-US Hospitals for Years 1999-2008* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5230J. Licensed under CC BY 4.0. Changed by Nextia Learning (see below). |
| Paper | Strack, B., DeShazo, J. P., Gennings, C., Olmo, J. L., Ventura, S., Cios, K. J., & Clore, J. N. (2014). Impact of HbA1c measurement on hospital readmission rates: analysis of 70,000 clinical database patient records. *BioMed Research International*, 2014, 781670. https://doi.org/10.1155/2014/781670 |
| Files used | `C05/case-studies/data/diabetes_130_hospitals.csv.gz`, SHA-256 `7e2cd49bd158b99bef449897d3f5118881dc469115c6e80189fd248355b08eac`, and `C05/case-studies/data/IDS_mapping.csv`, SHA-256 `f1bb82b471cb34649352597572c9b1fb00bd27f77b9f5a22a03dc3eb1039749e` |
| In the zips | The model bundle `bundles/readmission-1.0.0/` (12 KB model) and **derived discharge files** in `data/` (about 3.5 MB; see `data/README.md` in the zip). `training/train.py` downloads the two files above, checks their SHA-256, and makes the model and the discharge files again. |

## Changes made by Nextia Learning

1. The C05 preparation (as in the case study *Choose a model for hospital readmissions*): the 2,423 stays that ended in death or a hospice discharge are removed; the three code columns are translated to text with `IDS_mapping.csv` (the "unknown" codes become `unknown`); the main diagnosis (`diag_1`) is put in 9 groups as in Strack et al. (2014); the age band becomes its middle year; a missing specialty becomes `missing`, a missing test result `not measured`.
2. Split by patient with a fixed seed (60/20/20). The model learns from the train part (59,556 stays); the threshold comes from the valid part (20,179 stays).
3. The discharge files hold only the **test** part (19,608 stays of 13,852 patients), with the stay's number and the 19 features. They have **no** patient number, race, gender, payer, or target. The target is in a separate file, `outcomes_week.csv`, for checks only.
4. Two files are broken on purpose to teach partial failure: `discharges_typos.csv` (3 cells changed) and `discharges_hours.csv` (`time_in_hospital` × 24).
5. The case study calls the files "a week" and "a night" of discharges. The source has no dates: this is a teaching device, not a fact about the data.

## Checks that the case study runs

- `training/train.py` checks the SHA-256 of both source files, and gives the C05 numbers: test ROC AUC 0.663, average precision 0.217, 1,866 of 19,608 stays called at the threshold 0.18 (9.5%), precision 0.270, recall 0.221.
- The model file that it writes is byte for byte `model.joblib` of the bundle (scikit-learn 1.9.1, numpy 2.5.3, pandas 3.0.6, joblib 1.6.0; tested on macOS with Python 3.14.6).
- The service refuses a bundle with another digest, a changed file, or other package versions, and checks 10 parity cases at start-up.

## Known gaps and biases

- **Old data from one country**: US hospitals, 1999 to 2008, ICD-9 codes. Care, coding and insurance have changed since.
- **A weak signal**: ROC AUC 0.66. Readmission depends on things that the file does not record, such as help at home and follow-up care.
- **No dates**: the model could not be tested on later months, so we do not know how fast it ages.
- **Sensitive columns** (race, gender, payer) are not inputs. The C05 case study checks the model for each group; the results differ by age, and a real use needs those checks every month.
- **Health data about real people**, de-identified by the source. Do not try to re-identify anyone.
