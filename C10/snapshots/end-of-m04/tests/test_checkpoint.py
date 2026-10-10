"""Checkpoint and resume: the whole state survives the process."""

from resolver.checkpoint import CheckpointStore
from resolver.data import load_task
from resolver.runner import new_state


def test_save_and_load_the_whole_state(tmp_path):
    store = CheckpointStore(tmp_path / "runs.sqlite")
    s = new_state(load_task("T-90103"), "agent", "chat-small", "r-1")
    s.plan = ["look up the order", "propose"]
    s.log("note", "hello", x=1)
    store.save(s)
    back = CheckpointStore(tmp_path / "runs.sqlite").load("r-1")
    assert back.model_dump() == s.model_dump()
    assert store.latest("T-90103").run_id == "r-1"


def test_a_crashed_cli_run_resumes(capsys):
    from resolver.__main__ import main
    main(["run", "T-90104", "--variant", "agent", "--repeat", "1"])
    main(["runs"])
    assert "T-90104-agent-chat-small-1" in capsys.readouterr().out
