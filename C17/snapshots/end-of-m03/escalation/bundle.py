"""Load a model bundle safely, and refuse a bundle that is not the one we expect.

A bundle is a folder with everything the model needs to run:

    model.joblib       the fitted pipeline (preprocessing + model)
    contract.json      the features, their order and rules, and the threshold
    metadata.json      the version, the training data and the tested versions
    parity_cases.csv   fixed tickets and the scores they got in training
    SHA256SUMS         the SHA-256 of each file above

A joblib file can run code when it is loaded. So the checks run in this order,
and nothing is unpickled until the bytes are proven to be the expected ones.
"""

import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from escalation.contract import FEATURES

FILES = ["model.joblib", "contract.json", "metadata.json", "parity_cases.csv"]
PACKAGES = ["scikit-learn", "numpy", "pandas", "joblib"]
TOLERANCE = 1e-9


class BundleError(Exception):
    """The bundle is not safe or not right to serve. The service must not start."""


@dataclass
class Bundle:
    path: Path
    digest: str
    pipeline: object
    contract: dict
    metadata: dict

    @property
    def version(self) -> str:
        return self.metadata["model_version"]

    @property
    def threshold(self) -> float:
        return self.contract["output"]["threshold"]

    @property
    def known(self) -> dict[str, list[str]]:
        return self.contract["known_categories"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_digest(path: Path) -> str:
    """One fingerprint for the whole bundle: the SHA-256 of its SHA256SUMS file."""
    return sha256(path / "SHA256SUMS")


def check_files(path: Path, expected_digest: str) -> str:
    """Step 1 and 2: the bundle is the one we pinned, and no file has changed."""
    sums = path / "SHA256SUMS"
    if not sums.is_file():
        raise BundleError(f"{path}: no SHA256SUMS file")
    digest = bundle_digest(path)
    if digest != expected_digest:
        raise BundleError(
            f"{path}: the bundle digest is {digest[:12]}..., "
            f"but MODEL_SHA256 expects {expected_digest[:12]}..."
        )
    for line in sums.read_text(encoding="utf-8").splitlines():
        expected, name = line.split()
        if sha256(path / name) != expected:
            raise BundleError(f"{path / name}: the file changed after the bundle was made")
    return digest


def check_versions(metadata: dict) -> None:
    """Step 3: the packages here are the versions the bundle was tested with."""
    for package in PACKAGES:
        tested = metadata["versions"][package]
        installed = version(package)
        if installed != tested:
            raise BundleError(
                f"{package} {installed} is installed, "
                f"but the bundle was tested with {tested}"
            )


def self_check(bundle: Bundle) -> float:
    """Step 5: score the parity cases and compare with the training scores."""
    cases = pd.read_csv(
        bundle.path / "parity_cases.csv", keep_default_na=False, na_values=[""]
    )
    scores = bundle.pipeline.predict_proba(cases[FEATURES])[:, 1]
    largest = float(np.abs(scores - cases["expected_score"]).max())
    if largest > TOLERANCE:
        raise BundleError(
            f"self-check failed: scores differ from the bundle's by up to {largest:.1e}"
        )
    return largest


def load_bundle(path: str | Path, expected_digest: str) -> Bundle:
    path = Path(path)
    digest = check_files(path, expected_digest)
    contract = json.loads((path / "contract.json").read_text(encoding="utf-8"))
    metadata = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
    check_versions(metadata)

    pipeline = joblib.load(path / "model.joblib")  # step 4: only now

    fitted = list(pipeline.feature_names_in_)
    if fitted != contract["features"] or fitted != FEATURES:
        raise BundleError("the pipeline, the contract and this service list different features")
    bundle = Bundle(path, digest, pipeline, contract, metadata)
    self_check(bundle)
    return bundle
