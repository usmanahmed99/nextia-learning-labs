# Dataset card: Civil Comments with identity labels (CivilComments-WILDS v1.0), fixed sample

Used by: the case study *Regression-test a classifier release by slice* (https://learning.nextia-ai.com/courses/evals/m07/regression-test-a-classifier-release/), `regression-test-a-classifier-release.ipynb`

| Field | Value |
|---|---|
| Source | Civil Comments with the labels of the Jigsaw "Unintended Bias in Toxicity Classification" release (https://www.kaggle.com/c/jigsaw-unintended-bias-in-toxicity-classification/data; TFDS catalog https://www.tensorflow.org/datasets/catalog/civil_comments), in the WILDS version (https://wilds.stanford.edu/datasets/#civilcomments). File used: `all_data_with_identities.csv` from the Hugging Face mirror https://huggingface.co/datasets/shlomihod/civil-comments-wilds (revision `3fbfeca80bad0f3aec37e72fa07eff222b6e752f`; SHA-256 `403e638c83a225d738a937ff98b61fd0631e30f710d57928c7766d413526b77f`) |
| Publisher / creator | Comments: users of the Civil Comments platform (2015–2017), archived as public data when the platform closed. Labels: Jigsaw and Google's Conversation AI team, from crowd raters (Borkan, Dixon, Sorensen, Thain and Vasserman, "Nuanced Metrics for Measuring Unintended Bias with Real Data for Text Classification", WWW '19 Companion, arXiv:1903.04561). Split and group columns: WILDS (Koh et al., "WILDS: A Benchmark of in-the-Wild Distribution Shifts", ICML 2021, arXiv:2012.07421) |
| Licence | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/): "This dataset is released under CC0, as is the underlying comment text." WILDS: "This dataset is in the public domain and is distributed under CC0." |
| Attribution text | Not required by CC0. We credit: Civil Comments data with toxicity and identity labels by Jigsaw / Conversation AI (Borkan et al., 2019), WILDS version (Koh et al., 2021), CC0. Fixed sample by Nextia Learning. |
| Version or access date | WILDS v1.0, downloaded 2026-10-09 |
| Files used | `data/civil_comments_sample.csv.gz`, kept in `data/`: yes (CC0 allows it). Also the course's recorded outputs `scores.csv`, `train.json`, `statements.csv`, `new_comments.csv` and the rules `release_rules.json` |
| SHA-256 | `civil_comments_sample.csv.gz` a31eedbf043d8f866bf7cfaa1a4dfa89df9ec3d75106e916101be91b5c279576; `scores.csv` 625e3ae5096bfd753331f11ada6dddcb661c075c047d54f6b4ec236ede94c8a2; `statements.csv` c05843098dd307ae1ad6d7a16b956bcda217d4114a2706bcbd9d5d19548a7817; `new_comments.csv` 851f3df61e23669fbbd7fafd2b2238b8b341dfd8787d8f7f993f730c14e87db8; `train.json` 94ffec2c59ae9d53590564333f126204577822c4b6337748140b71b010a2e52d; `release_rules.json` 43aebb6a72cdbbb3c4d15564da9cf5e502c7cfdcacac3ef4335910362a88f950 |
| Size | 100,000 rows × 15 columns, 17.0 MB (gzip CSV) |

## What one row means

One public comment from an English-language news site (2015–2017). `toxicity` is the share of crowd raters who
said "toxic" or "very toxic"; the target is toxic = `toxicity` ≥ 0.5. The 8 group columns (`male`, `female`,
`LGBTQ`, `christian`, `muslim`, `other_religions`, `black`, `white`) are 1 when at least half of the raters said
the comment mentions that group. `part` is `train`, `dev` or `holdout`.

## Who made the labels, and what that means

Crowd raters made every label, using the Perspective API's rating guidelines (Borkan et al. 2019, §4.4). In this
sample the median comment has 4 toxicity raters, and 57% of holdout comments have exactly 4;
964 of the 3,393 toxic holdout comments are exactly 0.5 (for example 2 of 4 raters). The labels are
the judgement of a few people each, not a ground truth: borderline comments could have gone either way, and
raters' own views of what is toxic, or of which group a comment is about, are in the labels.

## Why this dataset

Its subgroups are groups of people, and the failure it was built to measure (a classifier that flags harmless
comments because they mention a group) is exactly a slice regression. CC0 allows us to host a fixed sample.
BANKING77 (CC BY 4.0) and CLINC150 (CC BY 3.0) were compared: their slices are intents and domains, not people,
and BANKING77 is already used in the LLM applications course. Full comparison:
`reference/c11/m07/l03/DATASET-RESEARCH.md` in the course repository.

## Changes we made

A fixed random sample (pandas `sample`, seed 2026): 60,000 comments of the WILDS train split (`train`),
10,000 of val (`dev`), 30,000 of test (`holdout`), sorted by `id`. Kept columns: `id`, `part`,
`created_date`, `toxicity`, `toxicity_annotator_count`, `identity_annotator_count`, the 8 groups as 0/1, and
`comment_text`. Nothing else changed. Builder: `reference/c11/m07/l03/build_sample.py`.

## Limitations and cautions

- **Offensive content.** Many comments are insulting or hateful, including about the groups in the labels.
- **Not a normal comment stream.** WILDS keeps only comments with identity labels, and some of those were chosen
  by models so that raters would see identity content often. 40% of holdout comments mention a group;
  rates do not describe a real site.
- **Only 8 groups.** People outside them (for example disabled people, or religions merged into
  `other_religions`) cannot be checked with these columns.
- **2015–2017, English, North-American news sites.** Language and norms change.
- Do not use the labels or the models to judge people, or to remove speech automatically.
