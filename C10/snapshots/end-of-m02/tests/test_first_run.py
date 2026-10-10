"""The known-good first run: the data is there, and a recorded run replays without an account."""

from resolver.__main__ import main
from resolver.data import load_tasks


def test_the_tasks_load():
    tasks = load_tasks()
    assert len(tasks) == 70
    slices = {}
    for t in tasks.values():
        slices[t.slice] = slices.get(t.slice, 0) + 1
    assert slices == {"simple": 16, "multi_step": 11, "needs_person": 10, "policy": 9, "adversarial": 8,
                      "failure": 8, "new_wording": 8}


def test_first_run_replays_a_recorded_decision(capsys):
    main(["run", "T-80008", "--variant", "agent", "--model", "chat-small"])
    out = capsys.readouterr().out
    assert "Outcome: reply_only (rule W1)" in out
    assert "Note:" not in out          # the exact recorded request: no warning
