"""The rules of the evaluation set: versions, splits and contamination checks."""

import pytest

from harness.dataset import CASES, DatasetProblem, check, inputs_version, load_cases, save_cases, version


def test_version_changes_with_one_character(tmp_path):
    cases = load_cases(split="all")
    path = tmp_path / "cases.jsonl"
    save_cases(cases, path)
    assert version(path) == version(CASES)  # the file's own format, byte for byte
    first = cases[0]
    changed = [first.model_copy(update={"text": first.text + "!"})] + cases[1:]
    save_cases(changed, path)
    assert version(path) != version(CASES)
    assert inputs_version(changed) != inputs_version(cases)


def test_a_label_change_keeps_the_inputs_version():
    cases = load_cases(split="all")
    first = cases[0]
    relabelled = [first.model_copy(update={"slice": "normal" if first.slice != "normal" else "boundary"})] + cases[1:]
    assert inputs_version(relabelled) == inputs_version(cases)


def test_a_contaminated_ticket_copied_into_dev_is_refused():
    cases = load_cases(split="all")
    tuned = next(c for c in cases if c.split == "contaminated" and c.text)
    copy = tuned.model_copy(update={"case_id": "T-99999", "split": "dev"})
    with pytest.raises(DatasetProblem, match="same text is in contaminated"):
        check(cases + [copy])


def test_needs_human_must_name_its_rule():
    cases = load_cases(split="all")
    first = next(c for c in cases if c.expected.needs_human)
    broken = first.model_copy(update={"expected": first.expected.model_copy(update={"rule": ""})})
    with pytest.raises(DatasetProblem, match="needs_human and rule disagree"):
        check([broken])


def test_every_label_names_who_made_it():
    assert all(c.label.by for c in load_cases(split="all"))
