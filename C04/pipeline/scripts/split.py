"""Split the modelling table by time: train on the past, test on the future."""

import json
from pathlib import Path

import pandas as pd

IN = Path("data/model/tickets_model.csv")
OUT = Path("data/model")
VALID_FROM = pd.Timestamp("2026-05-01")
TEST_FROM = pd.Timestamp("2026-06-01")


def main():
    df = pd.read_csv(IN, parse_dates=["created_at"])
    df["split"] = "train"
    df.loc[df["created_at"] >= VALID_FROM, "split"] = "valid"
    df.loc[df["created_at"] >= TEST_FROM, "split"] = "test"
    manifest = {"rule": f"train < {VALID_FROM.date()} <= valid < {TEST_FROM.date()} <= test", "parts": {}}
    for name in ["train", "valid", "test"]:
        part = df[df["split"] == name].drop(columns="split")
        part.to_csv(OUT / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        manifest["parts"][name] = {
            "rows": len(part), "escalated": int(part["escalated_72h"].sum()),
            "escalated_rate": round(part["escalated_72h"].mean(), 3),
            "first_created": str(part["created_at"].min()), "last_created": str(part["created_at"].max()),
        }
    train_customers = set(df.loc[df["split"] == "train", "customer_id"].dropna())
    test_customers = set(df.loc[df["split"] == "test", "customer_id"].dropna())
    manifest["test_customers_also_in_train"] = len(test_customers & train_customers)
    manifest["test_customers"] = len(test_customers)
    (OUT / "split_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
