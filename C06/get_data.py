"""Download Larkfield's tickets and the course's ticketnet.py into this folder, and check them.

    python get_data.py           download what is missing or changed
    python get_data.py --reset   delete data/ and ticketnet.py, then download everything again

Uses only Python's standard library. The tickets are synthetic (CC0): a language model wrote
them for this course from a list of situations; no real customer wrote them.
"""
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

LABS = os.environ.get("NX_LABS_RAW", "https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C06/")
FILES = {  # file -> SHA-256 (labs C06/data/SHA256SUMS)
    "data/train.csv": "98487169346f8b0d9bc55a3844849ab95d012b75f01d7083605a6a1cea57aa39",
    "data/valid.csv": "f0c7bfa75e75837cdaf891ac8d007a78a018ba8e3488155cf43f2c6a34a064c8",
    "data/test.csv": "f373f402bcc9742cdcf8829720710a97b7a1dce5d8e34aaa88d03e7e49a5404e",
    "data/split_manifest.json": "d043cf720697054fb16e6cfff72ecb49b471d75038308ad5836779a0dd0bf8a5",
}
HERE = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, path):
    try:
        urllib.request.urlretrieve(url, path)
    except OSError:  # Python without certificates (python.org on macOS): try curl
        if subprocess.run(["curl", "-fsSL", "-o", str(path), url]).returncode:
            sys.exit(f"Could not download {url}. Check your internet connection.")


if "--reset" in sys.argv:
    shutil.rmtree(HERE / "data", ignore_errors=True)
    (HERE / "ticketnet.py").unlink(missing_ok=True)

(HERE / "data").mkdir(exist_ok=True)
for name, expected in FILES.items():
    path = HERE / name
    if path.exists() and sha256(path) == expected:
        continue
    download(LABS + name, path)
    if sha256(path) != expected:
        sys.exit(f"{name} has the wrong checksum. Run: python get_data.py --reset")
    print("Downloaded", name)
if not (HERE / "ticketnet.py").exists():
    download(LABS + "project/ticketnet.py", HERE / "ticketnet.py")
    print("Downloaded ticketnet.py")

rows = {}
for part in ("train", "valid", "test"):
    with open(HERE / f"data/{part}.csv", newline="", encoding="utf-8") as fh:
        rows[part] = sum(1 for _ in csv.DictReader(fh))
print(f"Ready: train {rows['train']} tickets, valid {rows['valid']}, test {rows['test']}.")
