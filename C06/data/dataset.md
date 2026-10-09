# Dataset card: Larkfield ticket texts (deep learning course)

Used by: every lesson and notebook of *Deep Learning and Transformers Explained* (folder `C06/`).

| Field | Value |
|---|---|
| Source | Generated for the course: [`data-source/`](../data-source) has the scripts, the routing policy and every raw model reply |
| Publisher / creator | Nextia Learning. Texts written by Claude Haiku 5.5 and checked by Claude Sonnet 5.5 (Anthropic), 2026-10-08 |
| Licence | CC0 1.0 (public domain dedication) |
| Attribution text | None required. "Synthetic data from Nextia Learning" is welcome. |
| Version or access date | 1.0, generated 2026-10-08 |
| File used | `train.csv`, `valid.csv`, `test.csv`, `split_manifest.json`, kept in `data/`: yes |
| SHA-256 | See [`SHA256SUMS`](SHA256SUMS). The notebooks check every file. |
| Size | 5,896 tickets × 4 columns, about 1.7 MB |

## What one row means

One row is the first message of one support ticket to Larkfield, a fictional online shop for home and garden products. The target `team` is the help-desk team that must answer it: `delivery`, `returns`, `payment`, `warranty` or `account` (the routing rules are in [`routing_policy.md`](../data-source/routing_policy.md)).

| File | Rows | Teams |
|---|---|---|
| `train.csv` | 4,696 | delivery 1,279, payment 1,000, returns 940, warranty 800, account 677 |
| `valid.csv` | 600 | delivery 165, payment 126, returns 120, warranty 101, account 88 |
| `test.csv` | 600 | delivery 165, payment 126, returns 120, warranty 101, account 88 |

Columns: `ticket_id` (`T-60001`…), `text`, `team`, `style`.

`style` is **not an input** for a model. It records how the ticket was written, so that you can see where a model fails:

- `plain`: a clear ticket.
- `distractor`: mentions another team's topic in passing.
- `request_last`: the real request is in the last sentence.
- `negation`: says what the problem is not.
- `short`: 3 to 9 words.
- `typos`: informal, as typed on a phone.
- `long`: a story before the request.
- `boundary`: on one of the policy's boundaries (broken on arrival or after use; a refund before or after the return was confirmed; a saved card or a charge).
- `two_topics`: a solved problem from another team first, the real request last.

## How it was made

1. A script made 7,600 writing specifications: a team, a situation, a product, a style and a tone. 2,000 of them sit on the policy's boundaries, because an earlier test showed that ordinary tickets are too easy.
2. Claude Haiku 5.5 wrote one customer message for each specification. A few replies were cut off, so 7,447 messages exist.
3. Claude Sonnet 5.5 read each message and the routing policy, without the specification, and chose a team. 1,511 messages were not checked (the account ran out of credit), so they are not used.
4. A message was kept only when Sonnet's team equals the specification's team. 17 disagreed, 19 were "unclear", and 4 were exact duplicates; 5,896 were kept.
5. A random split, stratified by team: 600 test, 600 validation, the rest training.
6. **Label noise, on purpose:** 70 training rows (1.5%) got the team that people confuse most often with the right one, as in a real help desk. Their IDs are in `split_manifest.json` (`noisy_train_ids`). The validation and test files are clean.

`data-source/build_dataset.py` rebuilds the four files from the raw replies, byte for byte, with no API key.

## Why this dataset

The course needs one text task that runs on an ordinary computer and connects to the earlier courses. Routing tickets to the same five teams as in *Machine Learning: From Problem to Reliable Model* does both. Real help-desk tickets contain personal data and are not open; public complaint datasets are large and need cleaning that would hide the concepts. A generated set has no personal data and a clear licence. We can also control how hard it is, and record each ticket's writing style.

## Limitations and cautions

- The texts are synthetic. They are more regular than real tickets: fewer typos, no attachments, one language, one request per ticket.
- Two language models made the labels. Where both agree, the team is very likely right under the policy, but it is not a person's judgement.
- A simple word-count model scores very high on this data. That is a real result for this kind of task, not a flaw: the course uses it to show when a simple model is enough.
- Do not use the data to judge any real company, product or customer.
