"""The shared parts of Larkfield's escalation model: the columns, how to load
a part of the data, and the preprocessing-plus-model pipeline.

Nextia Learning, C05. You write this file in Module 2, lesson 3 (Preprocess
consistently), and add prior_escalations_90d in Module 3, lesson 3 (Select
useful features). train.py, evaluate.py and predict.py import it.
"""

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path("data")
CATEGORIES = ["channel", "team", "segment", "region"]
NUMBERS = ["priority", "order_value", "word_count", "customer_tenure_days", "prior_tickets_90d",
           "created_hour", "prior_escalations_90d"]
FEATURES = CATEGORIES + NUMBERS
TARGET = "escalated_72h"


def read(path):
    """Read a ticket CSV file. Only an empty cell is missing: the text
    "unknown" stays a category."""
    return pd.read_csv(path, parse_dates=["created_at"], dtype={"customer_id": "string"},
                       keep_default_na=False, na_values=[""])


def load(part):
    """One part of the split (train, valid or test), with the extra feature
    prior_escalations_90d from extra_features.csv."""
    df = read(DATA / f"{part}.csv")
    extra = pd.read_csv(DATA / "extra_features.csv", usecols=["ticket_id", "prior_escalations_90d"])
    return df.merge(extra, on="ticket_id", how="left", validate="one_to_one")


def build_pipeline(model=None):
    """Preprocessing and model in one object. fit() learns the medians, the
    scaling and the categories from the rows it is given, and nothing else."""
    numbers = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
    ])
    prepare = ColumnTransformer([
        ("categories", OneHotEncoder(handle_unknown="ignore"), CATEGORIES),
        ("numbers", numbers, NUMBERS),
    ])
    return Pipeline([("prepare", prepare), ("model", model if model is not None else LogisticRegression(max_iter=1000))])
