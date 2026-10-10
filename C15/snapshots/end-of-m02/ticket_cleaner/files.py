import csv
import json
import os
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    """Read raw records from a .csv or .json file."""
    if path.suffix == ".csv":
        with open(path, encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    raise ValueError(f"cannot read {path.name}: use a .csv or .json file")


def write_json(data: dict, path: Path) -> None:
    """Save data as JSON. Write a temporary file first, so a failure never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
    os.replace(temporary, path)
