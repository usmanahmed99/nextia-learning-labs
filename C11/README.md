# Evaluating and Testing AI Systems

Files for the course [Evaluating and Testing AI Systems](https://learning.nextia-ai.com/courses/evals/).

| Folder | What it has |
|---|---|
| [`data/`](data) | The evaluation set: 271 support tickets of Larkfield (synthetic) with their labels, splits and slices, Grace's policy, the [dataset card](data/dataset.md) and the script that builds it. CC0. |
| [`snapshots/`](snapshots) | The course project `eval-harness`: `start` (download it in the lesson *Choose evaluation layers*) and the project at the end of each module. Code MIT; data and recorded outputs CC0, except one public sample of human ratings (CC BY 4.0, see its README). |
| [`M07-L01-calibrate-a-model-judge/`](M07-L01-calibrate-a-model-judge) | Case study *Calibrate a model judge against human ratings*: learner and solution notebooks, a fixed sample of MT-Bench human votes (CC BY 4.0) and the recorded verdicts of two model judges, with a [dataset card](M07-L01-calibrate-a-model-judge/dataset.md). |
| [`M07-L02-evaluate-summaries-against-expert-ratings/`](M07-L02-evaluate-summaries-against-expert-ratings) | Case study *Evaluate summaries against expert ratings*: learner and solution notebooks, the judge prompt, the recorded model judge scores and a Wikinews article (CC BY 4.0), with a [dataset card](M07-L02-evaluate-summaries-against-expert-ratings/dataset.md). The notebook downloads the SummEval ratings and the CNN/DailyMail articles from their sources; they are not stored here. |
| [`M07-L03-regression-test-a-classifier-release/`](M07-L03-regression-test-a-classifier-release) | Case study *Regression-test a classifier release by slice*: learner and solution notebooks, a fixed sample of 100,000 Civil Comments (CC0; some comments are offensive), the saved scores of both model versions and the release rules, with a [dataset card](M07-L03-regression-test-a-classifier-release/dataset.md). |

You need no account and no key. Every output of the assistant and every verdict of a model judge was recorded from a real model and is saved here. A live judge is optional (a free local model through Ollama, or your own key), with a usage cap in the code.
