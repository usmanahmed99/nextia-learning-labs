import shutil

import costmodel.components
import costmodel.demand
import costmodel.inputs
import costmodel.packcheck
from costmodel.inputs import ROOT
from costmodel.packcheck import CHECKS, run


def test_the_pack_passes_every_check():
    passed, lines = run()
    assert passed == len(CHECKS), "\n".join(lines)


def copy_pack(tmp_path, monkeypatch):
    shutil.copytree(ROOT, tmp_path / "pack", ignore=shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache"))
    for module in (costmodel.inputs, costmodel.packcheck, costmodel.components, costmodel.demand):
        monkeypatch.setattr(module, "ROOT", tmp_path / "pack")
    return tmp_path / "pack"


def test_an_adr_without_revisit_fails(tmp_path, monkeypatch):
    pack = copy_pack(tmp_path, monkeypatch)
    adr = next((pack / "decisions").glob("adr-*.md"))
    adr.write_text(adr.read_text(encoding="utf-8").replace("## Revisit when", "## Later"), encoding="utf-8")
    passed, lines = run()
    assert passed == len(CHECKS) - 1
    assert any("FAIL  decisions" in line and "Revisit when" in line for line in lines)


def test_a_failure_without_an_owner_fails(tmp_path, monkeypatch):
    pack = copy_pack(tmp_path, monkeypatch)
    f = pack / "decisions/failure-modes.md"
    f.write_text(f.read_text(encoding="utf-8").replace("| Mei | minutes (resize) |", "|  | minutes (resize) |"),
                 encoding="utf-8")
    passed, lines = run()
    assert any("FAIL  failures" in line for line in lines)
