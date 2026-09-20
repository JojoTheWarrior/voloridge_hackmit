"""Read-only adapter over the WarSignal ``missions/`` folder.

Contract (used by every scene; keep the field names stable):

* ``DataAdapter(root, poll_interval=2.0).snapshot()`` returns a cached
  :class:`Snapshot`, re-reading disk at most every ``poll_interval`` seconds.
* Everything is defensive: missing files/fields never raise.
"""
from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


_TS_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s*[\t|]\s*(.*)$")
_RUN_DIR = re.compile(r"^(\d{8})-(\d{3})-(.+)$")
_NULLISH = {"", "none", "nan", "null"}
_QUEUE_ROUND = re.compile(r"^R\d+$")
_QUEUE_PARENT = re.compile(r"^[A-Z]{1,3}\d*-[0-9A-Za-z]+$")
LIVE_STATES = {"queued", "running"}
DONE_STATES = {"done", "failed"}


def _read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_bytes().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _num(value) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in _NULLISH:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or math.isinf(out):  # drop NaN and inf
        return None
    return out


def _pick_num(*values) -> Optional[float]:
    for value in values:
        num = _num(value)
        if num is not None:
            return num
    return None


def _pick_str(*values) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


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


def agent_tag(url: str) -> str:
    """Last path segment of a session URL, first 8 chars (``""`` when absent)."""
    if not url:
        return ""
    return url.rstrip("/").rsplit("/", 1)[-1][:8]


def _clip01(value: Optional[float]) -> Optional[float]:
    return None if value is None else max(0.0, min(1.0, value))


@dataclass
class ActiveMission:
    hypothesis: str
    started_at: float  # unix seconds
    validity: Optional[float] = None  # 0-10 when known
    perm_p: Optional[float] = None
    mission_id: str = ""
    title: str = ""
    stage: str = ""
    state: str = "running"
    progress: Optional[float] = None  # 0-1
    live_signal: Optional[float] = None
    message: str = ""
    agent_session_url: str = ""
    updated_at: Optional[float] = None
    round: str = ""
    parent_mission_id: str = ""

    @property
    def display_title(self) -> str:
        return self.title or self.hypothesis

    @property
    def agent_tag(self) -> str:
        return agent_tag(self.agent_session_url)

    def elapsed(self, now: Optional[float] = None) -> float:
        return max(0.0, (now if now is not None else time.time()) - self.started_at)

    def signal(self) -> Optional[float]:
        """0.0 (noise) .. 1.0 (signal), or None when no stats exist yet."""
        if self.live_signal is not None:
            return max(0.0, min(1.0, self.live_signal))
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
    best_lag: Optional[int] = None
    viz_path: Optional[Path] = None
    note_path: Optional[Path] = None
    actionability: Optional[float] = None
    trade_idea: Optional[dict] = None
    stage: str = ""
    message: str = ""
    agent_session_url: str = ""
    parent_mission_id: str = ""
    round: str = ""
    followup_hypothesis: str = ""

    @property
    def agent_tag(self) -> str:
        return agent_tag(self.agent_session_url)

    @property
    def failed(self) -> bool:
        return self.status == "failed" or "-FAILED-" in self.folder

    def age(self, now: Optional[float] = None) -> Optional[float]:
        """Seconds since ``created_at``, or None when unknown."""
        if self.created_at is None:
            return None
        return max(0.0, (now if now is not None else time.time()) - self.created_at)

    def signal(self) -> Optional[float]:
        return signal_strength(self.validity, self.perm_p)

    def note_text(self) -> str:
        return _read_text(self.note_path) if self.note_path else ""


@dataclass
class Snapshot:
    queue: list[str] = field(default_factory=list)
    queue_items: list["QueueItem"] = field(default_factory=list)
    active: list[ActiveMission] = field(default_factory=list)
    completed: list[CompletedMission] = field(default_factory=list)  # newest first
    failed: list[tuple[str, str]] = field(default_factory=list)  # (hypothesis, error)
    loaded_at: float = 0.0

    @property
    def succeeded(self) -> list[CompletedMission]:
        return [m for m in self.completed if not m.failed]

    @property
    def counts(self) -> dict:
        return {
            "active": len(self.active),
            "queued": len(self.queue),
            "completed_ok": sum(1 for m in self.completed if not m.failed),
            "failed": sum(1 for m in self.completed if m.failed),
            "live": sum(1 for m in self.active if m.mission_id),
        }


def signal_strength(validity: Optional[float], perm_p: Optional[float]) -> Optional[float]:
    if validity is not None:
        return max(0.0, min(1.0, validity / 10.0))
    if perm_p is not None:
        return max(0.0, min(1.0, 1.0 - perm_p))
    return None


def read_queue(path: Path) -> list[str]:
    return [line.strip() for line in _read_text(path).splitlines() if line.strip()]


@dataclass
class QueueItem:
    text: str
    round: str = ""
    parent_mission_id: str = ""


def parse_queue_line(line: str) -> QueueItem:
    """``R2 | R2-0017 | hypothesis`` -> QueueItem(round, parent, text)."""
    cells = [c.strip() for c in line.split("|")]
    round_ = ""
    parent = ""
    if cells and _QUEUE_ROUND.match(cells[0]):
        round_ = cells.pop(0)
    if cells and _QUEUE_PARENT.match(cells[0]):
        parent = cells.pop(0)
    return QueueItem(text=" | ".join(cells).strip(), round=round_, parent_mission_id=parent)


# -- live status files (missions/status/<mission_id>.json) ---------------------

def read_status(path: Path) -> Optional[dict]:
    """Parse one status JSON; ``None`` unless it's a dict with mission_id+state."""
    data = _read_json(path)
    if not data or not _pick_str(data.get("mission_id")) or not _pick_str(data.get("state")):
        return None
    return data


def read_statuses(status_dir: Path) -> list[dict]:
    """All ``*.json`` directly under ``missions/status/`` sorted by mission_id."""
    out = []
    try:
        children = list(Path(status_dir).iterdir())
    except OSError:
        return out
    for child in children:
        try:
            if not child.is_file() or child.suffix != ".json":
                continue
        except OSError:
            continue
        status = read_status(child)
        if status is not None:
            status["_path"] = child
            out.append(status)
    out.sort(key=lambda s: str(s.get("mission_id") or ""))
    return out


def _status_ts(status: dict, key: str) -> Optional[float]:
    value = status.get(key)
    return _parse_ts(str(value)) if isinstance(value, str) else None


def active_from_status(status: dict, path: Path) -> ActiveMission:
    started = _status_ts(status, "started_at")
    if started is None:
        updated = _status_ts(status, "updated_at")
        if updated is not None:
            started = updated - (_num(status.get("elapsed_s")) or 0.0)
    if started is None:
        try:
            started = Path(path).stat().st_mtime
        except OSError:
            started = time.time()
    return ActiveMission(
        hypothesis=_pick_str(status.get("hypothesis"), status.get("title")),
        started_at=started,
        mission_id=_pick_str(status.get("mission_id")),
        title=_pick_str(status.get("title")),
        stage=_pick_str(status.get("stage")),
        state=_pick_str(status.get("state"), "running"),
        progress=_clip01(_num(status.get("progress"))),
        live_signal=_clip01(_num(status.get("signal"))),
        message=_pick_str(status.get("message")),
        agent_session_url=_pick_str(status.get("agent_session_url")),
        updated_at=_status_ts(status, "updated_at"),
        round=_pick_str(status.get("round")),
        parent_mission_id=_pick_str(status.get("parent_mission_id")),
    )


def _status_scores(status: dict) -> dict:
    scores = status.get("scores")
    return scores if isinstance(scores, dict) else {}


def merge_status_into_completed(mission: CompletedMission, status: dict) -> None:
    """Fill empty fields on a run-derived mission from its status file."""
    scores = _status_scores(status)
    if mission.validity is None:
        mission.validity = _num(scores.get("validity"))
    if mission.interestingness is None:
        mission.interestingness = _num(scores.get("interestingness"))
    if mission.unexpectedness is None:
        mission.unexpectedness = _num(scores.get("unexpectedness"))
    if mission.actionability is None:
        mission.actionability = _num(scores.get("actionability"))
    if mission.trade_idea is None and isinstance(status.get("trade_idea"), dict):
        mission.trade_idea = status["trade_idea"]
    for field_name, key in (("agent_session_url", "agent_session_url"), ("parent_mission_id", "parent_mission_id"),
                            ("round", "round"), ("message", "message"), ("stage", "stage"),
                            ("followup_hypothesis", "followup_hypothesis"), ("mission_id", "mission_id"),
                            ("hypothesis", "hypothesis")):
        if not getattr(mission, field_name):
            setattr(mission, field_name, _pick_str(status.get(key)))
    if status.get("state") == "failed":
        mission.status = "failed"


def completed_from_status(status: dict, root: Path) -> CompletedMission:
    """Synthesize a CompletedMission for a done/failed status with no run folder."""
    scores = _status_scores(status)
    run_folder = _pick_str(status.get("run_folder"))
    folder = Path(run_folder).name if run_folder else ""
    mission_id = _pick_str(status.get("mission_id"))
    path = Path(root) / run_folder if run_folder else Path(root) / "missions" / "runs" / (folder or mission_id)
    try:
        viz = path / "viz.png"
        viz_path = viz if viz.is_file() else None
        note = path / "note.md"
        note_path = note if note.is_file() else None
    except OSError:
        viz_path = note_path = None
    state = _pick_str(status.get("state"), "done")
    return CompletedMission(
        folder=folder or mission_id,
        path=path,
        hypothesis=_pick_str(status.get("hypothesis"), status.get("title")),
        status="failed" if state == "failed" else "ok",
        mission_id=mission_id,
        created_at=_status_ts(status, "finished_at") or _status_ts(status, "updated_at"),
        validity=_num(scores.get("validity")),
        interestingness=_num(scores.get("interestingness")),
        unexpectedness=_num(scores.get("unexpectedness")),
        actionability=_num(scores.get("actionability")),
        trade_idea=status.get("trade_idea") if isinstance(status.get("trade_idea"), dict) else None,
        stage=_pick_str(status.get("stage")),
        message=_pick_str(status.get("message")),
        agent_session_url=_pick_str(status.get("agent_session_url")),
        parent_mission_id=_pick_str(status.get("parent_mission_id")),
        round=_pick_str(status.get("round")),
        followup_hypothesis=_pick_str(status.get("followup_hypothesis")),
        viz_path=viz_path,
        note_path=note_path,
    )


def apply_statuses(snapshot_parts: dict, root: Path, statuses: list[dict]) -> None:
    """Merge ``missions/status/*.json`` into the active/completed lists."""
    completed = snapshot_parts["completed"]
    by_folder = {m.folder: m for m in completed}
    by_id = {m.mission_id: m for m in completed if m.mission_id}
    actives = []
    status_names = set()
    for status in statuses:
        state = str(status.get("state") or "")
        status_names.add(_pick_str(status.get("hypothesis")))
        status_names.add(_pick_str(status.get("title")))
        if state in LIVE_STATES:
            actives.append(active_from_status(status, status.get("_path", "")))
        elif state in DONE_STATES:
            run_folder = _pick_str(status.get("run_folder"))
            folder = Path(run_folder).name if run_folder else ""
            match = by_folder.get(folder) or by_id.get(_pick_str(status.get("mission_id")))
            if match is not None:
                merge_status_into_completed(match, status)
            else:
                completed.append(completed_from_status(status, root))
    status_names.discard("")
    for legacy in snapshot_parts["active"]:
        if legacy.hypothesis.strip() not in status_names:
            actives.append(legacy)
    snapshot_parts["active"] = actives
    completed.sort(key=lambda m: (bool(m.mission_id) and m.folder == m.mission_id, m.folder), reverse=True)


def _inflight_stats(runs_dir: Path, hypothesis: str) -> tuple[Optional[float], Optional[float]]:
    """Look for live stats of an in-flight mission.

    Today this always returns ``(None, None)``: the mission runner only
    creates the run folder (via ``write_run_folder``) after the mission
    finishes, so no on-disk stats exist while a mission is in flight.
    Kept as a hook in case the pipeline ever streams partial results.
    """
    try:
        children = list(runs_dir.iterdir())
    except OSError:
        return None, None
    for child in children:
        try:
            if not child.is_dir() or not _RUN_DIR.match(child.name):
                continue
            hyp = _read_text(child / "hypothesis.txt").strip()
            if not hyp or hyp != hypothesis.strip():
                continue
            manifest = _read_json(child / "manifest.json")
            status = str(manifest.get("status") or "")
            if manifest and status in {"ok", "failed"}:
                continue
            stats = _read_json(child / "stats.json")
            judge = _read_json(child / "judge.json")
            scores = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
            validity = _pick_num(manifest.get("validity"), scores.get("validity"))
            perm_p = _pick_num(manifest.get("perm_p"), stats.get("perm_p"))
            if validity is not None or perm_p is not None:
                return validity, perm_p
        except OSError:
            continue
    return None, None


def read_active(
    path: Path,
    now: Optional[float] = None,
    runs_dir: Optional[Path] = None,
) -> list[ActiveMission]:
    """Parse ``in_progress.txt`` into ActiveMissions.

    The queue appends plain hypothesis lines and rewrites the file
    atomically on completion, so the file mtime is the only start-time
    proxy and is shared by every line in the file. Lines may optionally
    carry an ISO-timestamp prefix (``<ts>\\t<hypothesis>``) which wins
    over the mtime when present.
    """
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
        mission = ActiveMission(hypothesis=line, started_at=started)
        if runs_dir is not None:
            mission.validity, mission.perm_p = _inflight_stats(runs_dir, line)
        out.append(mission)
    return out


def read_failed(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in _read_text(path).splitlines():
        if not line.strip():
            continue
        hyp, _, err = line.partition("\t")
        rows.append((hyp.strip(), err.strip()))
    return rows


def read_index(path: Path) -> dict[str, dict]:
    """Parse ``missions/runs/INDEX.md`` into ``{folder: row}``.

    The index is a markdown table with columns
    ``folder | hypothesis | status | n | r | perm_p | Validity | Interest | Unexpected``.
    Tolerant of any file size and shape: non-table lines are skipped and
    it never raises.
    """
    out: dict[str, dict] = {}
    for line in _read_text(path).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 9:
            continue
        folder = cells[0].strip("`").strip()
        if not _RUN_DIR.match(folder):
            continue
        out[folder] = {
            "hypothesis": cells[1],
            "status": cells[2],
            "n_obs": _num(cells[3]),
            "r": _num(cells[4]),
            "perm_p": _num(cells[5]),
            "validity": _num(cells[6]),
            "interestingness": _num(cells[7]),
            "unexpectedness": _num(cells[8]),
        }
    return out


def read_run(path: Path, index: Optional[dict[str, dict]] = None) -> Optional[CompletedMission]:
    try:
        if not path.is_dir() or not _RUN_DIR.match(path.name):
            return None
    except OSError:
        return None
    row = (index or {}).get(path.name) or {}
    manifest = _read_json(path / "manifest.json")
    stats = _read_json(path / "stats.json")
    judge = _read_json(path / "judge.json")
    scores = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
    corr = stats.get("correlation") if isinstance(stats.get("correlation"), dict) else {}
    lagged = stats.get("lagged") if isinstance(stats.get("lagged"), dict) else {}
    best_lag = _pick_num(manifest.get("best_lag"), lagged.get("best_lag"), row.get("best_lag"))
    hypothesis = _pick_str(
        manifest.get("hypothesis"),
        row.get("hypothesis"),
        _read_text(path / "hypothesis.txt"),
    )
    created = _parse_ts(str(manifest.get("created_at", ""))) if manifest.get("created_at") else None
    if created is None:
        try:
            created = path.stat().st_mtime
        except OSError:
            created = None
    status = _pick_str(
        manifest.get("status"),
        row.get("status"),
        "failed" if "-FAILED-" in path.name else "unknown",
    )
    n_obs = _pick_num(manifest.get("n_obs"), stats.get("n_obs"), row.get("n_obs"))
    try:
        viz = path / "viz.png"
        viz_path = viz if viz.is_file() else None
        note = path / "note.md"
        note_path = note if note.is_file() else None
    except OSError:
        viz_path = note_path = None
    return CompletedMission(
        folder=path.name,
        path=path,
        hypothesis=hypothesis,
        status=status,
        mission_id=_pick_str(manifest.get("mission_id")),
        created_at=created,
        n_obs=int(n_obs) if n_obs is not None else None,
        r=_pick_num(manifest.get("r"), corr.get("pearson_r"), row.get("r")),
        perm_p=_pick_num(manifest.get("perm_p"), stats.get("perm_p"), row.get("perm_p")),
        validity=_pick_num(manifest.get("validity"), scores.get("validity"), row.get("validity")),
        interestingness=_pick_num(manifest.get("interestingness"), scores.get("interestingness"), row.get("interestingness")),
        unexpectedness=_pick_num(manifest.get("unexpectedness"), scores.get("unexpectedness"), row.get("unexpectedness")),
        best_lag=int(best_lag) if best_lag is not None else None,
        viz_path=viz_path,
        note_path=note_path,
    )


def read_runs(
    runs_dir: Path,
    index: Optional[dict[str, dict]] = None,
    cache: Optional[dict] = None,
) -> list[CompletedMission]:
    try:
        children = list(runs_dir.iterdir())
    except OSError:
        children = []
    seen = set()
    out = []
    for child in children:
        mission = None
        if cache is not None:
            try:
                dir_mtime = child.stat().st_mtime
            except OSError:
                continue
            try:
                manifest_mtime = (child / "manifest.json").stat().st_mtime
            except OSError:
                manifest_mtime = None
            cached = cache.get(child.name)
            if cached is not None and cached[0] == dir_mtime and cached[1] == manifest_mtime:
                mission = cached[2]
            else:
                mission = read_run(child, index)
                if mission is not None:
                    cache[child.name] = (dir_mtime, manifest_mtime, mission)
                else:
                    cache.pop(child.name, None)
            seen.add(child.name)
        else:
            mission = read_run(child, index)
        if mission is not None:
            out.append(mission)
    if cache is not None:
        for name in list(cache):
            if name not in seen:
                del cache[name]
    out.sort(key=lambda m: m.folder, reverse=True)
    return out


def _overlay_statuses(local: list[dict], overlay: list[dict]) -> list[dict]:
    """Merge overlay statuses over local ones (later ``updated_at`` wins)."""
    by_id = {str(s.get("mission_id") or ""): s for s in local}
    for over in overlay:
        mid = str(over.get("mission_id") or "")
        existing = by_id.get(mid)
        if existing is not None:
            t_over = _status_ts(over, "updated_at")
            t_local = _status_ts(existing, "updated_at")
            if t_over is not None and t_local is not None and t_local > t_over:
                continue
        by_id[mid] = over
    return sorted(by_id.values(), key=lambda s: str(s.get("mission_id") or ""))


def load_snapshot(
    root: Path,
    now: Optional[float] = None,
    cache: Optional[dict] = None,
    overlay: Optional[Path] = None,
) -> Snapshot:
    missions = Path(root) / "missions"
    now = now if now is not None else time.time()
    runs_dir = missions / "runs"
    index = read_index(runs_dir / "INDEX.md")
    overlay_dir = Path(overlay) if overlay else None
    if overlay_dir is not None and not overlay_dir.exists():
        overlay_dir = None

    def pick(name: str) -> Path:
        if overlay_dir is not None and (overlay_dir / name).exists():
            return overlay_dir / name
        return missions / name

    queue_lines = read_queue(pick("queue.txt"))
    parts = {
        "queue": queue_lines,
        "queue_items": [parse_queue_line(line) for line in queue_lines],
        "active": read_active(pick("in_progress.txt"), now, runs_dir=runs_dir),
        "completed": read_runs(runs_dir, index=index, cache=cache),
        "failed": read_failed(pick("failed.txt")),
        "loaded_at": now,
    }
    try:
        statuses = read_statuses(missions / "status")
        if overlay_dir is not None:
            statuses = _overlay_statuses(statuses, read_statuses(overlay_dir / "status"))
    except OSError:
        statuses = []
    if statuses:
        apply_statuses(parts, Path(root), statuses)
    return Snapshot(**parts)


class DataAdapter:
    def __init__(self, root: Path, poll_interval: float = 2.0, overlay: Optional[Path] = None):
        self.root = Path(root)
        self.poll_interval = poll_interval
        self.overlay = overlay
        self._snapshot: Optional[Snapshot] = None
        self._run_cache: dict = {}

    def refresh(self, now: Optional[float] = None) -> Snapshot:
        now = now if now is not None else time.time()
        try:
            self._snapshot = load_snapshot(self.root, now, cache=self._run_cache, overlay=self.overlay)
        except Exception:
            if self._snapshot is None:
                self._snapshot = Snapshot(loaded_at=now)
            else:
                self._snapshot = Snapshot(
                    queue=self._snapshot.queue,
                    active=self._snapshot.active,
                    completed=self._snapshot.completed,
                    failed=self._snapshot.failed,
                    loaded_at=now,
                )
        return self._snapshot

    def snapshot(self, now: Optional[float] = None) -> Snapshot:
        now = now if now is not None else time.time()
        if self._snapshot is None or now - self._snapshot.loaded_at >= self.poll_interval:
            return self.refresh(now)
        return self._snapshot
