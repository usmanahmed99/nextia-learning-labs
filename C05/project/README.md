# C05 project: the course's finished files

The files of your `ticket-model` project as they are at the end of C05. Use them to catch up: copy a file into your project folder if your own version is broken, then continue the lesson.

| File | Written in |
|---|---|
| `ticket_model.py` | Module 4, [Preprocess with a pipeline](https://learning.nextia-ai.com/courses/ml/m04/preprocess-with-a-pipeline/); `prior_escalations_90d` added in Module 6, [Select useful features](https://learning.nextia-ai.com/courses/ml/m06/select-useful-features/) |
| `train.py` | Module 8, [Package artifacts](https://learning.nextia-ai.com/courses/ml/m08/package-artifacts/) (the threshold rule is from Module 6, [Thresholds and calibration](https://learning.nextia-ai.com/courses/ml/m06/thresholds-and-calibration/)) |
| `evaluate.py` | Module 6, [Thresholds and calibration](https://learning.nextia-ai.com/courses/ml/m06/thresholds-and-calibration/#test-once-with-evaluatepy), finished in Module 8 |
| `predict.py` | Module 8, [Package artifacts](https://learning.nextia-ai.com/courses/ml/m08/package-artifacts/) and [Plan production checks](https://learning.nextia-ai.com/courses/ml/m08/plan-production-checks/) |
| `requirements.txt` | Module 8, [Package artifacts](https://learning.nextia-ai.com/courses/ml/m08/package-artifacts/) |

Run them from your project folder, next to `data/`, in an environment with `requirements.txt` installed:

```bash
python train.py
python predict.py --check
python evaluate.py
python predict.py data/july_tickets.csv predictions.csv
```

Expected first line of `python train.py`: `Trained on 16939 tickets. Threshold 0.19 for a review capacity of 20%.`
