import json
import shutil

import pytest

from escalation.bundle import BundleError, bundle_digest, load_bundle
from tests.conftest import BUNDLE


@pytest.fixture
def copy(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(BUNDLE, target)
    return target


def test_the_pinned_bundle_loads():
    bundle = load_bundle(BUNDLE, bundle_digest(BUNDLE))
    assert bundle.version == "1.0.0"
    assert bundle.threshold == 0.19


def test_a_wrong_digest_stops_before_loading(copy, monkeypatch):
    loaded = []
    monkeypatch.setattr("escalation.bundle.joblib.load", lambda path: loaded.append(path))
    with pytest.raises(BundleError, match="MODEL_SHA256 expects"):
        load_bundle(copy, "0" * 64)
    assert loaded == []


def test_a_changed_file_is_found(copy):
    digest = bundle_digest(copy)
    with open(copy / "model.joblib", "ab") as model:
        model.write(b"\0")
    with pytest.raises(BundleError, match="changed after the bundle was made"):
        load_bundle(copy, digest)


def test_other_package_versions_are_refused(copy, monkeypatch):
    monkeypatch.setattr("escalation.bundle.version", lambda package: "0.0.1")
    with pytest.raises(BundleError, match="was tested with"):
        load_bundle(copy, bundle_digest(copy))


def test_a_self_check_failure_stops_the_bundle(copy):
    cases = (copy / "parity_cases.csv").read_text(encoding="utf-8").splitlines()
    header, first = cases[0], cases[1].rsplit(",", 1)
    cases[1] = f"{first[0]},0.5"
    (copy / "parity_cases.csv").write_text("\n".join(cases) + "\n", encoding="utf-8")
    sums = [line for line in (copy / "SHA256SUMS").read_text().splitlines()]
    import hashlib

    new = hashlib.sha256((copy / "parity_cases.csv").read_bytes()).hexdigest()
    sums = [f"{new}  parity_cases.csv" if line.endswith("parity_cases.csv") else line for line in sums]
    (copy / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    with pytest.raises(BundleError, match="self-check failed"):
        load_bundle(copy, bundle_digest(copy))


def test_the_contract_lists_the_pipeline_features():
    contract = json.loads((BUNDLE / "contract.json").read_text())
    assert len(contract["features"]) == 11
