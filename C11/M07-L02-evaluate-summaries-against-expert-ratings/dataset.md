# Dataset card: SummEval expert ratings, with the CNN/DailyMail articles

Used by: the case study "Evaluate summaries against expert ratings" (Evaluating and Testing AI Systems, Module 7), `evaluate-summaries-against-expert-ratings.ipynb`

| Field | Value |
|---|---|
| Source | Ratings and summaries: https://github.com/Yale-LILY/SummEval (file `model_annotations.aligned.jsonl`, linked from the README: https://storage.googleapis.com/sfr-summarization-repo-research/model_annotations.aligned.jsonl). Articles and highlights: https://huggingface.co/datasets/abisee/cnn_dailymail, configuration 3.0.0, test split, revision `96df5e686bee6baa90b8bee7c28b81fa3fa6223d` |
| Publisher / creator | SummEval: Alexander R. Fabbri, Wojciech Kryściński, Bryan McCann, Caiming Xiong, Richard Socher, Dragomir Radev (Yale LILY Lab and Salesforce Research). CNN/DailyMail: Hermann et al. (2015), non-anonymised version by See et al. (2017); the texts belong to CNN and the Daily Mail |
| Licence | SummEval repository: MIT (https://github.com/Yale-LILY/SummEval/blob/master/LICENSE); the annotations are released with it. The annotation file has no licence file of its own. The CNN/DailyMail article texts are the publishers' copyright |
| Attribution text | Ratings and summaries: SummEval (Fabbri et al., 2021, "SummEval: Re-evaluating Summarization Evaluation", Transactions of the ACL 9, 391–409), MIT licence. Articles: the CNN/DailyMail dataset (Hermann et al., 2015; See et al., 2017). The summaries were written by 16 summarisation systems; please also cite their papers (listed in the SummEval README) |
| Version or access date | Downloaded 2026-10-09 (SummEval file of 2020-04-19; CNN/DailyMail revision above) |
| File used | Neither file is kept in this folder: the notebook downloads both from their sources and checks them. This folder holds only the course's own files (below) |
| SHA-256 | `model_annotations.aligned.jsonl`: `f0d4166e0cdeb439b387c4449634b067b7e9f721b9ef4c2b722f6b7550d3d6ab` · `3.0.0/test-00000-of-00001.parquet`: `04e322d2634a96dba76bf9a6294fbbe48e0b36abeae43f13d86ba2c3bebffe4e` |
| Size | 1,600 summaries (100 articles × 16 systems), 5.8 MB; the CNN/DailyMail test file has 11,490 articles, 30 MB, of which the notebook uses the 100 that SummEval rated |

## What one row means

One row is **one summary** of one news article, written by one of 16 summarisation systems from 2017–2020. It has **three expert ratings** and **five crowd ratings**, each from 1 (worst) to 5 (best), on four qualities: **coherence** (the summary as a whole is well organised), **consistency** (every fact is supported by the article), **fluency** (each sentence is well formed) and **relevance** (it keeps the important content and nothing else). The target of the case study is the mean of the three expert ratings, per quality.

## Who rated

From the SummEval paper (section 4): the **experts** were three people "who have written papers on summarization either for academic conferences (2) or as part of a senior thesis (1)". They rated in **two rounds**: in the second round they re-checked the scores that were more than 2 points away from the others, and they could see the other experts' first-round scores. The **crowd** ratings come from five Amazon Mechanical Turk workers per summary (at least 10,000 approved tasks, 97% approval, in the United States, the United Kingdom or Australia). The paper reports Krippendorff's alpha of 0.49 (crowd), 0.41 (experts, round 1) and 0.71 (experts, round 2).

No rating in this dataset was made by the course. The **model judge ratings** in `recordings/` are model outputs, not human ratings.

## The course's own files in this folder

| File | What it is |
|---|---|
| `recordings/judge_chat-small.jsonl`, `recordings/judge_chat-strong.jsonl` | The model judge's scores for the 800 summaries of 50 articles (10 dev, 40 holdout; 752 scored by `chat-strong`, 751 by `chat-small`): gpt-6-luna (`chat-small`) and gpt-6.1-sol (`chat-strong`) on Azure, recorded 2026-10-09 with `prompts/judge_v1.md`. One line per summary: the SummEval ID and system, the four scores, the judge's note on the first unsupported statement, tokens, latency, and the content-filter refusals. No article text |
| `prompts/judge_v1.md` | The judge's prompt with a rubric per quality, written from the SummEval definitions |
| `new_input/article.json` | A Wikinews article (CC BY 4.0, revision 5010348) for the end-to-end run, with its attribution |
| `new_input/judgements.json` | The summary of that article written by `chat-small`, two CONSTRUCTED variants (one changed number; one that misses the main point), and both judges' verdicts |

## Why this dataset

It is the only open set we found with **expert** ratings of **summaries** on **several qualities**, with three experts per summary (so the experts' own agreement is a ceiling for any measure) and crowd ratings for contrast. Compared in `DATASET-RESEARCH.md`: SEAHORSE (CC BY 4.0, but one non-expert rater and yes/no answers), HANNA (stories, crowd raters), WMT MQM (experts, but translation) and FRANK (factuality only).

## Changes we made

None to the downloaded files. The notebook joins the two files by article ID, takes the mean of the three expert ratings, and splits the 100 articles into 10 dev, 40 holdout and 50 not judged (`random.Random(2026)` on the sorted IDs). All measures are computed in the notebook.

## Limitations and cautions

- **Old systems.** The 16 systems date from 2017–2020; their typical errors (repeated or garbled phrases) are rarer in today's models. Which measure works best may change with the systems you evaluate.
- **The expert round 2 raises agreement.** Experts saw each other's first-round scores, so their agreement is higher than independent ratings would be.
- **Most summaries are rated consistent and fluent.** About 87% of summaries have an expert mean that rounds to 5 for consistency, and 81% for fluency. With so few faults, correlations on these two qualities rest on a small number of summaries.
- **Most summaries are lower case and tokenised** (spaces around punctuation): they are the systems' raw output. Two systems, M20 and M22, wrote normal case.
- **News content.** Some articles report crimes, accidents and violence. Azure's content filter refused every judge request for 3 of the 50 judged articles, on both deployments (two crimes, one injury; 48 summaries), and `chat-small` also refused 1 summary of a fourth article. These summaries have no judge score.
- **One reference per article.** ROUGE in the notebook uses the original highlights only; SummEval also has 10 crowd-written references, not used here.
