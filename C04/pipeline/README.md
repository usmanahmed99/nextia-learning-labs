# C04 pipeline: the course's finished scripts

The queries and scripts that you write in C04, as they are at the end of the course. Use them to:

- **catch up**: copy a script into your `ticket-data` project if your own version is broken, then continue the lesson;
- **run a lesson notebook**: the notebooks from Module 4 on download these files to rebuild the steps of earlier lessons.

| File | Written in |
|---|---|
| `queries/extract_tickets.sql`, `queries/extract_outcomes.sql`, `scripts/extract.py` | Module 3, [Reproducible extraction](https://learning.nextia-ai.com/courses/sql/m03/reproducible-extraction/) |
| `scripts/clean.py` | Module 4, [Handle messy values](https://learning.nextia-ai.com/courses/sql/m04/handle-messy-values/) |
| `scripts/build_features.py` | Module 5, [Features and target timing](https://learning.nextia-ai.com/courses/sql/m05/features-and-target-timing/) |
| `scripts/split.py` | Module 5, [Choose a split](https://learning.nextia-ai.com/courses/sql/m05/choose-a-split/) |
| `scripts/check_input.py`, `scripts/validate.py` | Module 6, [Validation rules](https://learning.nextia-ai.com/courses/sql/m06/validation-rules/) |
| `run_pipeline.py` | Module 6, [Deliver a reusable dataset](https://learning.nextia-ai.com/courses/sql/m06/deliver-a-reusable-dataset/) |

Run them from your project folder, next to `larkfield.db`, with pandas 3.0.6 installed: for example `python scripts/clean.py`.
