from __future__ import annotations

import os
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_ACTIVE_DIR = ROOT / "missions"


def _rewrite(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.writelines(lines)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def pop_next(queue_path=ROOT / "missions" / "queue.txt"):
    global _ACTIVE_DIR
    queue_path = Path(queue_path)
    _ACTIVE_DIR = queue_path.parent
    lines = queue_path.read_text(encoding="utf-8").splitlines(True) if queue_path.exists() else []
    index = next((i for i, line in enumerate(lines) if line.strip()), None)
    if index is None:
        return None
    line = lines.pop(index).strip()
    _rewrite(queue_path, lines)
    with (queue_path.parent / "in_progress.txt").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return line


def mark_done(line):
    path = _ACTIVE_DIR / "in_progress.txt"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    _rewrite(path, [x + "\n" for x in lines if x != line])


def mark_failed(line, err):
    mark_done(line)
    with (_ACTIVE_DIR / "failed.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"{line}\t{err}\n")


def requeue_failed():
    path = _ACTIVE_DIR / "failed.txt"
    if not path.exists():
        return 0
    rows = path.read_text(encoding="utf-8").splitlines()
    with (_ACTIVE_DIR / "queue.txt").open("a", encoding="utf-8") as queue:
        for row in rows:
            queue.write(row.split("\t", 1)[0] + "\n")
    path.unlink()
    return len(rows)
