"""Download the C05 practice data into data/ and check it.

Nextia Learning, C05: Machine Learning: From Problem to Reliable Model.

Run it in your project folder (~/projects/ticket-model):

    python get_data.py           download what is missing, check every file
    python get_data.py --reset   delete data/ and download everything again

Standard library only; Python 3.12 or later. The data is synthetic: the
Larkfield help desk is made up for the course and has no real people.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

LABS = "https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C05/data/"
DATA = Path("data")
FILES = {
    "train.csv": "63b8732a28e891189cc28a9bcd505a093a9c4c51c01f3d0e1fba6d4959242d53",
    "valid.csv": "3604df83ea2ec3cec70c2eedfc7e95cc6d5cb82ccfc3b5cf565e614783e2bde2",
    "test.csv": "60e89f75e4d7d59ccfbda49ca719ce7f8e8d97c0380256d633ab240d546771ec",
    "split_manifest.json": "b9957927041144bb62ba84f8c46bf8651cfe92e32684add8998ec2e8bbf68a2c",
    "extra_features.csv": "03c6da28bcb347982aa70a7c72b869771a6cb055654d629da924512c6fd56563",
    "daily_tickets.csv": "7deba76b112b4133a5d16b74be7e2b331ce28c7064e7fd8dd471768e5f1ba360",
    "july_tickets.csv": "10dffc093993341a361172d0aa6ea0e7c06521f140cc2a80ee90c713361f7c99",
    "july_labels.csv": "3163c57e398db6fd1c19e505548d0fa1464821ef96c77901a759abbd3a8605fa",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, path):
    try:
        urllib.request.urlretrieve(url, path)
    except OSError:
        # Python from python.org on macOS can lack root certificates: try curl.
        if subprocess.run(["curl", "-fsSL", "-o", str(path), url]).returncode:
            sys.exit(f"Could not download {url}. Check your internet connection, then run again.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="delete data/ and download everything again")
    args = parser.parse_args()
    if args.reset and DATA.exists():
        shutil.rmtree(DATA)
        print("Deleted data/.")
    DATA.mkdir(exist_ok=True)
    for name, expected in FILES.items():
        path = DATA / name
        if path.exists() and sha256(path) == expected:
            continue
        download(LABS + name, path)
        if sha256(path) != expected:
            sys.exit(f"{name} has the wrong checksum. Run: python get_data.py --reset")
        print(f"Downloaded {name}")
    counts = {}
    for part in ("train", "valid", "test"):
        with open(DATA / f"{part}.csv", encoding="utf-8") as f:
            rows = f.read().splitlines()[1:]
        counts[part] = (len(rows), sum(row.endswith(",1") for row in rows))
    print("Ready: train {} rows ({} escalated), valid {} ({}), test {} ({}).".format(
        *counts["train"], *counts["valid"], *counts["test"]))


if __name__ == "__main__":
    main()
