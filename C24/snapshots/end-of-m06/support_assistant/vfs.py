"""A small sandboxed file reader for the assistant's file area.

The server keeps files under data/vfs/files/<tenant>/<ticket>/... The `read_file` tool must only
read a file that belongs to the current ticket. The weak version reads any path the model gives,
which lets a path like ../../config/service.env escape the ticket folder. The safe version resolves
the path against an allowed base and refuses anything outside it.
"""

from pathlib import Path


class FileDenied(Exception):
    code = "file_denied"


def read_unsafe(base: Path, rel_path: str) -> str:
    """Join and read with no checks (the weak version): a ../ escapes the folder.

    One guard protects YOUR computer, not the practice server: a path that leaves the practice file
    area (base's parent, which holds files/ and config/) reads nothing.
    """
    target = (base / rel_path).resolve()
    if base.resolve().parent not in target.parents:
        raise FileNotFoundError(rel_path)
    return target.read_text(encoding="utf-8")


def read_sandboxed(root: Path, allowed_prefix: str, rel_path: str) -> str:
    """Read a file only if it stays inside root/allowed_prefix. Otherwise refuse.

    `root` is data/vfs/files. `allowed_prefix` is <tenant>/<ticket>. `rel_path` is what the model asked
    for: either the bare file name or the full stored path (<tenant>/<ticket>/<name>). An absolute
    path, a drive letter or a ../ that leaves the ticket's folder is refused.
    """
    rel = rel_path.replace("\\", "/")
    if rel.startswith("/") or (len(rel) > 1 and rel[1] == ":"):
        raise FileDenied(f"{rel_path}: an absolute path is not allowed.")
    base = (root / allowed_prefix).resolve()
    # Try the path as given (relative to files/), then as a name inside the ticket folder.
    for candidate in ((root / rel).resolve(), (base / rel).resolve()):
        if candidate == base or base in candidate.parents:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
    # If any reading of the path pointed outside the ticket folder, say so plainly.
    raise FileDenied(f"{rel_path}: that file is not in this ticket's folder.")
