# Machine Learning: From Problem to Reliable Model

Practice files for the course at [learning.nextia-ai.com/courses/ml/](https://learning.nextia-ai.com/courses/ml/).

| Path | What it is |
|---|---|
| `data/` | The Larkfield help-desk modelling data: `train.csv`, `valid.csv`, `test.csv`, extra columns, daily ticket counts and the July tickets. Read [`data/dataset.md`](data/dataset.md). |
| `generate.py` | Makes everything in `data/` (seed 5010, standard library only). |
| `get_data.py` | Downloads `data/` into your project folder and checks every file's SHA-256. |
| `project/` | The course's finished project files: `ticket_model.py`, `train.py`, `evaluate.py`, `predict.py` and `requirements.txt`. Copy one if your own version is broken, then continue the lesson. |
| `Mnn-Lnn-<slug>/` | The lesson notebooks. Each one downloads what it needs, so you can open any lesson without the earlier ones. |
| `M09-Lnn-<slug>/` | The seven case studies: real public datasets, from the raw file to a tested result. Complete at least one for the certificate. |
| `case-studies/data/` | The case-study datasets as fixed gzip CSV copies, each with a dataset card (source, licence, attribution, the changes we made) and `SHA256SUMS`. |

## Start a local project

You can do every lesson in Colab or Kaggle without an installation. To work on your own computer instead (Python 3.12 or later):

```bash
mkdir -p ~/projects/ticket-model && cd ~/projects/ticket-model
curl -fsSL -O https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C05/get_data.py
python3 get_data.py
```

On Windows PowerShell, use `curl.exe` and `python`. The last line should be:

```
Ready: train 16939 rows (1983 escalated), valid 1179 (183), test 1002 (157).
```

`python3 get_data.py --reset` deletes `data/` and downloads it again.

All data is synthetic: Larkfield and its customers are made up, and there are no real people.
