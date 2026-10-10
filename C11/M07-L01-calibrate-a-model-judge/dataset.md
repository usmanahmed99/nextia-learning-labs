# Dataset card: MT-Bench human judgments (fixed sample with recorded model judges)

Used by: the case study *Calibrate a model judge against human ratings* (https://learning.nextia-ai.com/courses/evals/m07/calibrate-a-model-judge/), `calibrate-a-model-judge.ipynb`

| Field | Value |
|---|---|
| Source | https://huggingface.co/datasets/lmsys/mt_bench_human_judgments (revision `f7d2896d2cc5d80f8b55c2bbc722613555233c25`); categories, reference answers and judge prompts from https://github.com/lm-sys/FastChat (commit `587d5cfa1609a43d192cedb8441cac3c17db105d`) |
| Publisher / creator | LMSYS: Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023), arXiv:2306.05685 |
| Licence | Human judgments: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). FastChat files: [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0). Recorded judgments (`judgments.jsonl`): made by Nextia Learning, same terms as the course's labs |
| Attribution text | Data: MT-Bench human judgments, LMSYS (Zheng et al., 2023, arXiv:2306.05685), licensed under CC BY 4.0. Reference answers, categories and judge prompts: lm-sys/FastChat (Apache-2.0). Changes: 320 first-turn items with votes from 2 or more human judges (40 per category), some fields kept, labels in a fixed model order, category, dev/holdout split by question and reference answers added. |
| Version or access date | 2026-10-09 |
| Files used | `data/mtb_judge_sample.jsonl`, `data/judgments.jsonl`, kept in `data/`: yes (CC BY 4.0 allows sharing) |
| SHA-256 | `mtb_judge_sample.jsonl` 7a6a3e2f52dca0d05a65669def84d5d55637be9d74388e2ba50b22afbc1cbf58; `judgments.jsonl` 48c91b7c4bc08d93b6157277c842ee6a83811f8173c1a315322bb5b3a9969f7c |
| Size | 320 items, 834 human votes; 1760 recorded judgments |

## What one row means

`mtb_judge_sample.jsonl`: one MT-Bench question (first turn), the answers of two chatbots of 2023 (`model_1` is the
alphabetically first name), and the votes of 2 to 7 human judges: `A` (answer 1 better), `B` (answer 2 better) or `tie`.
`gpt4_2023` is GPT-4's pairwise verdict from the same dataset (`inconsistent` = it changed with the order).
`judgments.jsonl`: one recorded call of an Azure model judge (`chat-small` = gpt-6-luna-2026-09-22, `chat-strong` =
gpt-6.1-sol-2026-09-29) with the paper's prompt `pair-v2` (no reference) or `pair-math-v1` (with the reference
answer), in order `12` (answer 1 shown as Assistant A) or `21`. `letter` is what the judge wrote; `outcome` is `ok`,
`refused` (Azure's content filter), `unparsed` or `error`.

## Who made the ratings

The human votes were made by "58 expert-level human labelers … mostly graduate students" from more than ten
universities, paid US$20 for 20 questions, and by some of the paper's authors (rater IDs `expert_N` and `author_N`).
When a vote differed from GPT-4, the collection tool showed GPT-4's judgment and asked whether it was reasonable;
the paper reports that people changed their choice in 34% of those cases. The data does not say which votes changed.
The model verdicts are model outputs, never human ratings.

## Why this dataset

It has several independent human votes per item with rater IDs (so the human-to-human ceiling can be measured), eight
categories, reference answers for reasoning, math and coding, and a published GPT-4 judge on the same items, under
CC BY 4.0. HelpSteer3 (CC BY 4.0) was compared: it releases only the three annotations that agree most, which inflates
agreement by design, and it has no rater IDs. Full comparison: `reference/c11/m07/l01/DATASET-RESEARCH.md` in the
course repository.

## Changes we made

Turn 1 only; one vote per judge per item; items with 2 or more different judges (484), then 40 per category with
`random.Random(711)`; labels in a fixed direction; category, split (5 of 10 questions per category are dev,
`random.Random(2026)`) and the reference answer (questions 101–130) added.

## Limitations and cautions

- The answers are from 2023 chatbots; some are wrong. Do not read them as advice.
- The human judges are mostly graduate students, not users of a product; their taste is one taste.
- Some human votes may have been changed after seeing GPT-4's judgment (see above).
- 20 items per category on dev: category results have wide intervals.
- The model judges are a snapshot of 2026-10-09; a new model version needs a new calibration.
