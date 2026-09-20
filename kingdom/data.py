"""Read-only adapter over the WarSignal ``missions/`` folder.

Contract (used by every scene; keep the field names stable):

* ``DataAdapter(root, poll_interval=2.0).snapshot()`` returns a cached
  :class:`Snapshot`, re-reading disk at most every ``poll_interval`` seconds.
* Everything is defensive: missing files/fields never raise.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_TS_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s*[\t|]\s*(.*)$")
_RUN_DIR = re.compile(r"^(\d{8})-(\d{3})-(.+)$")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _num(value) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # drop NaN


def _parse_ts(text: str) -> Optional[float]:
    text = text.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


@dataclass
class ActiveMission:
    hypothesis: str
    started_at: float  # unix seconds
    validity: Optional[float] = None  # 0-10 when known
    perm_p: Optional[float] = None

    def elapsed(self, now: Optional[float] = None) -> float:
        return max(0.0, (now if now is not None else time.time()) - self.started_at)

    def signal(self) -> Optional[float]:
        """0.0 (noise) .. 1.0 (signal), or None when no stats exist yet."""
        return signal_strength(self.validity, self.perm_p)


@dataclass
class CompletedMission:
    folder: str
    path: Path
    hypothesis: str = ""
    status: str = "unknown"  # ok | failed | unknown
    mission_id: str = ""
    created_at: Optional[float] = None
    n_obs: Optional[int] = None
    r: Optional[float] = None
    perm_p: Optional[float] = None
    validity: Optional[float] = None
    interestingness: Optional[float] = None
    unexpectedness: Optional[float] = None
    viz_path: Optional[Path] = None
    note_path: Optional[Path] = None

    @property
    def failed(self) -> bool:
        return self.status == "failed" or "-FAILED-" in self.folder

    def signal(self) -> Optional[float]:
        return signal_strength(self.validity, self.perm_p)

    def note_text(self) -> str:
        return _read_text(self.note_path) if self.note_path else ""


@dataclass
class Snapshot:
    queue: list[str] = field(default_factory=list)
    active: list[ActiveMission] = field(default_factory=list)
    completed: list[CompletedMission] = field(default_factory=list)  # newest first
    failed: list[tuple[str, str]] = field(default_factory=list)  # (hypothesis, error)
    loaded_at: float = 0.0

    @property
    def succeeded(self) -> list[CompletedMission]:
        return [m for m in self.completed if not m.failed]


def signal_strength(validity: Optional[float], perm_p: Optional[float]) -> Optional[float]:
    if validity is not None:
        return max(0.0, min(1.0, validity / 10.0))
    if perm_p is not None:
        return max(0.0, min(1.0, 1.0 - perm_p))
    return None


def read_queue(path: Path) -> list[str]:
    return [line.strip() for line in _read_text(path).splitlines() if line.strip()]


def read_active(path: Path, now: Optional[float] = None) -> list[ActiveMission]:
    if not path.exists():
        return []
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = now if now is not None else time.time()
    out = []
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line:
            continue
        started = mtime
        match = _TS_PREFIX.match(line)
        if match:
            ts = _parse_ts(match.group(1))
            if ts is not None:
                started, line = ts, match.group(2).strip()
        out.append(ActiveMission(hypothesis=line, started_at=started))
    return out


def read_failed(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in _read_text(path).splitlines():
        if not line.strip():
            continue
        hyp, _, err = line.partition("\t")
        rows.append((hyp.strip(), err.strip()))
    return rows


def read_run(path: Path) -> Optional[CompletedMission]:
    if not path.is_dir() or not _RUN_DIR.match(path.name):
        return None
    manifest = _read_json(path / "manifest.json")
    stats = _read_json(path / "stats.json")
    judge = _read_json(path / "judge.json")
    scores = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
    hypothesis = manifest.get("hypothesis") or _read_text(path / "hypothesis.txt").strip()
    corr = stats.get("correlation") if isinstance(stats.get("correlation"), dict) else {}
    n_obs = _num(manifest.get("n_obs", stats.get("n_obs")))
    created = _parse_ts(str(manifest.get("created_at", ""))) if manifest.get("created_at") else None
    if created is None:
        try:
            created = path.stat().st_mtime
        except OSError:
            created = None
    status = str(manifest.get("status") or ("failed" if "-FAILED-" in path.name else "unknown"))
    viz = path / "viz.png"
    note = path / "note.md"
    return CompletedMission(
        folder=path.name,
        path=path,
        hypothesis=str(hypothesis or ""),
        status=status,
        mission_id=str(manifest.get("mission_id", "")),
        created_at=created,
        n_obs=int(n_obs) if n_obs is not None else None,
        r=_num(manifest.get("r", corr.get("pearson_r"))),
        perm_p=_num(manifest.get("perm_p", stats.get("perm_p"))),
        validity=_num(manifest.get("validity", scores.get("validity"))),
        interestingness=_num(manifest.get("interestingness", scores.get("interestingness"))),
        unexpectedness=_num(manifest.get("unexpectedness", scores.get("unexpectedness"))),
        viz_path=viz if viz.is_file() else None,
        note_path=note if note.is_file() else None,
    )


def read_runs(runs_dir: Path) -> list[CompletedMission]:
    if not runs_dir.is_dir():
        return []
    out = []
    for child in runs_dir.iterdir():
        mission = read_run(child)
        if mission is not None:
            out.append(mission)
    out.sort(key=lambda m: m.folder, reverse=True)
    return out


def load_snapshot(root: Path, now: Optional[float] = None) -> Snapshot:
    missions = Path(root) / "missions"
    now = now if now is not None else time.time()
    return Snapshot(
        queue=read_queue(missions / "queue.txt"),
        active=read_active(missions / "in_progress.txt", now),
        completed=read_runs(missions / "runs"),
        failed=read_failed(missions / "failed.txt"),
        loaded_at=now,
    )


class DataAdapter:
    def __init__(self, root: Path, poll_interval: float = 2.0):
        self.root = Path(root)
        self.poll_interval = poll_interval
        self._snapshot: Optional[Snapshot] = None

    def refresh(self, now: Optional[float] = None) -> Snapshot:
        self._snapshot = load_snapshot(self.root, now)
        return self._snapshot

    def snapshot(self, now: Optional[float] = None) -> Snapshot:
        now = now if now is not None else time.time()
        if self._snapshot is None or now - self._snapshot.loaded_at >= self.poll_interval:
            return self.refresh(now)
        return self._snapshot
