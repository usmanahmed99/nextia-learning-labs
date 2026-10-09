# Calibration sample

30 replies of Larkfield's assistant (15 tickets of the development set, two systems), shown blind: the item IDs are shuffled and the system is not named.

- `items.jsonl`: what you rate. Each item has the ticket, the reference notes and the reply.
- `sheet_blank.csv`: copy it, write a score from 1 to 5 for each item with the rubric (`harness/prompts/rubric.md`), and save it.
- `reference_ratings.csv`: the course author's ratings, made with the same rubric before any model judge was run. Open it only after you rate. It is one person's reading, not the truth: compare, and discuss where you differ.
- `key.json`: which case and run each item comes from. Open it last.

Then: `python -m harness agree data/calibration/reference_ratings.csv my_ratings.csv`.
