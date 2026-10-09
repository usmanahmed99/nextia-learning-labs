"""Run IDs: readable, stable, and different when one setting changes."""

from harness.run import find_run, load_outputs, load_runs, make_run_id


def test_the_baseline_run():
    run = find_run("baseline")
    assert run.run_id.startswith("baseline-v2-chat-small-r1-")
    assert run.model_version.startswith("gpt-6-luna")
    assert len(load_outputs(run)) == run.cases == 271


def test_one_changed_setting_gives_another_id():
    args = ["baseline", "v2", "abc", "chat-small", "263bbd4f180d", 1, "2026-10-09T14:43:00-04:00"]
    assert make_run_id(*args) == make_run_id(*args)
    assert make_run_id(*args[:5], 2, args[6]) != make_run_id(*args)


def test_every_run_names_its_dataset_version():
    assert all(len(r.dataset_version) == 12 and len(r.inputs_version) == 12 for r in load_runs().values())
