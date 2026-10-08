# Start: the machine learning course's model, for learners who do not have it

Use this folder only if you do not have your own `ticket-model` project from
*Machine Learning: From Problem to Reliable Model* with a trained `model/`.
[Prediction inputs and outputs](https://learning.nextia-ai.com/courses/serving/m01/prediction-inputs-and-outputs/) says when you need it.

| File | What it is |
|---|---|
| `model/escalation_model.joblib` | The fitted pipeline (preprocessing + logistic regression), made by the machine learning course's `train.py` |
| `model/model_info.json` | Its feature schema, threshold 0.19, versions and data checksums |
| `model/check_sample.csv` | 20 validation tickets and their scores |
| `data/valid.csv`, `data/extra_features.csv` | The machine learning course's data that `make_bundle.py` reads for the parity cases |

**Check the model before you load it.** A joblib file can run code when it is
loaded ([Artifact trust and integrity](https://learning.nextia-ai.com/courses/serving/m01/artifact-trust-and-integrity/)).
Its SHA-256 must be exactly:

```text
a4acd259a398e7c84517b98bf50d811197f90b0f2f1ea15f1f9e168ba3aff736  escalation_model.joblib
```

macOS/Linux: `shasum -a 256 model/escalation_model.joblib`.
Windows (PowerShell): `(Get-FileHash model\escalation_model.joblib -Algorithm SHA256).Hash.ToLower()`.

A bundle made from this folder with `python make_bundle.py <this folder> --version 1.0.0`
has the course's digest `8f233029aa4c896dce1a5b3dfa970cd085088386bbe7784519f15a5b1a433b74`
(scikit-learn 1.9.1, pandas 3.0.6, numpy 2.5.3, joblib 1.6.0; tested on macOS).

The data is synthetic (the machine learning course's Larkfield data); see `C05/data/dataset.md`.
