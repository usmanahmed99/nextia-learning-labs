"""The file reader for the assistant's file area.

The server keeps files under data/vfs/files/<tenant>/<ticket>/... (your practice copy is in work/vfs).
This first reader joins the path the model gives to the file area and reads it, with no checks: a
path like ../config/service.env leaves the attachments and reaches the server's own config.
"""

from pathlib import Path


def read_unsafe(base: Path, rel_path: str) -> str:
    """Join and read with no checks (the weak version): a ../ escapes the folder.

    One guard protects YOUR computer, not the practice server: a path that leaves the practice file
    area (base's parent, which holds files/ and config/) reads nothing.
    """
    target = (base / rel_path).resolve()
    if base.resolve().parent not in target.parents:
        raise FileNotFoundError(rel_path)
    return target.read_text(encoding="utf-8")
