"""Read-only monitor over the WarSignal ``missions/`` folder.

Merges ``missions/status/*.json`` progress files, run folders under
``missions/runs/``, ``queue.txt``, ``results.csv`` and ``failed.txt`` into a
single JSON-serialisable state dict for the terminal web UI. GitHub ``main``
is the source of truth: :class:`Monitor` runs ``git pull --rebase --autostash``
on a fixed interval before re-reading disk. Every loader is defensive —
missing files and malformed JSON never raise.
"""
from __future__ import annotations

import csv
import io
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from kingdom.data import (
    _num,
    _parse_ts,
    _pick_num,
    _pick_str,
    _read_json,
    _read_text,
    _RUN_DIR,
    read_failed,
    read_index,
    read_queue,
    read_runs,
    signal_strength,
)

STAGES = [
    "queued",
    "planning",
    "loading",
    "stats",
    "judging",
    "narrative",
    "viz",
    "trade",
    "followup",
    "publishing",
    "done",
]

_SCORE_KEYS = ("validity", "interestingness", "unexpectedness", "actionability")
_QUEUE_BRACKET = re.compile(r"^\[([^\]<]+?)(?:\s*<-\s*([^\]]+))?\]\s*(.*)$")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_from_ts(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def _status_file(path: Path, now: float) -> dict:
    data = _read_json(path)
    stage = _pick_str(data.get("stage"))
    progress = _num(data.get("progress"))
    if progress is None:
        progress = STAGES.index(stage) / 10.0 if stage in STAGES else 0.0
    progress = max(0.0, min(1.0, progress))
    state = _pick_str(data.get("state")) or "running"
    started_at = _pick_str(data.get("started_at")) or None
    finished_at = _pick_str(data.get("finished_at")) or None
    elapsed = _num(data.get("elapsed_s"))
    if elapsed is None:
        started_ts = _parse_ts(started_at or "")
        if state == "running":
            elapsed = (now - started_ts) if started_ts is not None else 0.0
        else:
            finished_ts = _parse_ts(finished_at or "")
            if started_ts is not None and finished_ts is not None:
                elapsed = finished_ts - started_ts
            else:
                elapsed = 0.0
    scores_in = data.get("scores") if isinstance(data.get("scores"), dict) else {}
    scores = {key: _num(scores_in.get(key)) for key in _SCORE_KEYS}
    brains = data.get("brain_sessions")
    brain_sessions = [
        {"purpose": _pick_str(b.get("purpose") if isinstance(b, dict) else ""),
         "session_url": _pick_str(b.get("session_url") if isinstance(b, dict) else "")}
        for b in brains if isinstance(b, dict)
    ] if isinstance(brains, list) else []
    return {
        "mission_id": _pick_str(data.get("mission_id")) or path.stem,
        "title": _pick_str(data.get("title")) or None,
        "hypothesis": _pick_str(data.get("hypothesis")) or None,
        "parent_mission_id": _pick_str(data.get("parent_mission_id")) or None,
        "round": _pick_str(data.get("round")) or None,
        "agent_session_url": _pick_str(data.get("agent_session_url")) or None,
        "brain_sessions": brain_sessions,
        "state": state,
        "stage": stage or None,
        "progress": progress,
        "signal": _num(data.get("signal")),
        "started_at": started_at,
        "updated_at": _pick_str(data.get("updated_at")) or None,
        "finished_at": finished_at,
        "elapsed_s": int(max(0.0, elapsed)),
        "message": _pick_str(data.get("message")) or None,
        "run_folder": _pick_str(data.get("run_folder")) or None,
        "scores": scores,
        "trade_idea": data.get("trade_idea"),
        "followup_hypothesis": data.get("followup_hypothesis"),
        "file": path.name,
    }


def read_status_dir(status_dir: Path, now: float) -> list[dict]:
    """Normalise every ``*.json`` directly inside ``status_dir``."""
    try:
        files = sorted(Path(status_dir).glob("*.json"))
    except OSError:
        files = []
    out = []
    for path in files:
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        out.append(_status_file(path, now))

    def _key(entry: dict):
        rank = {"running": 0, "queued": 1}.get(entry["state"], 2)
        started = _parse_ts(entry.get("started_at") or "")
        return (rank, started if started is not None else float("inf"), entry["mission_id"])

    out.sort(key=_key)
    return out


def parse_queue_line(line: str) -> dict:
    """Parse one ``queue.txt`` line into ``{round, parent_id, hypothesis}``.

    Supported forms: ``[<round>] hyp``, ``[<round> <- <parent>] hyp``,
    tab-separated ``round<TAB>parent<TAB>hypothesis``, and a plain hypothesis.
    """
    line = line.strip()
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t")]
        if len(parts) >= 3:
            return {"round": parts[0], "parent_id": parts[1], "hypothesis": "\t".join(parts[2:]).strip()}
    match = _QUEUE_BRACKET.match(line)
    if match:
        return {
            "round": (match.group(1) or "").strip(),
            "parent_id": (match.group(2) or "").strip(),
            "hypothesis": match.group(3).strip(),
        }
    return {"round": "", "parent_id": "", "hypothesis": line}


def read_queue_entries(path: Path) -> list[dict]:
    entries = []
    for pos, line in enumerate(read_queue(path), start=1):
        entry = parse_queue_line(line)
        entry["position"] = pos
        entries.append(entry)
    return entries


def read_results_csv(path: Path) -> dict:
    """``missions/results.csv`` as ``{mission_id: row}`` (``folder`` fallback)."""
    text = _read_text(path)
    if not text.strip():
        return {}
    out = {}
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            if not isinstance(row, dict):
                continue
            key = _pick_str(row.get("mission_id")) or _pick_str(row.get("folder"))
            if key:
                out[key] = row
    except csv.Error:
        return {}
    return out


def _best_lag(lagged: dict) -> tuple[Optional[int], Optional[float]]:
    """Best lag as the max-|r| entry of ``stats['lagged']``."""
    if not isinstance(lagged, dict):
        return None, None
    best_lag = lagged.get("best_lag")
    best_r = _num(lagged.get("best_r"))
    lags = lagged.get("lags")
    rs = lagged.get("r")
    if isinstance(lags, list) and isinstance(rs, list) and len(lags) == len(rs) and rs:
        pairs = [(_num(l), _num(r)) for l, r in zip(lags, rs)]
        pairs = [(l, r) for l, r in pairs if r is not None]
        if pairs:
            lag, r = max(pairs, key=lambda p: abs(p[1]))
            if best_r is None or abs(r) > abs(best_r):
                best_lag, best_r = lag, r
    try:
        best_lag = int(best_lag) if best_lag is not None else None
    except (TypeError, ValueError):
        best_lag = None
    return best_lag, best_r


def read_run_details(run_dir: Path, status: Optional[dict] = None) -> dict:
    """Full detail dict for one run folder (defensive, never raises)."""
    run_dir = Path(run_dir)
    manifest = _read_json(run_dir / "manifest.json")
    stats = _read_json(run_dir / "stats.json")
    judge = _read_json(run_dir / "judge.json")
    scores_in = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
    corr = stats.get("correlation") if isinstance(stats.get("correlation"), dict) else {}
    lagged = stats.get("lagged") if isinstance(stats.get("lagged"), dict) else {}
    best_lag, best_r = _best_lag(lagged)
    trade = _read_json(run_dir / "trade_idea.json")
    if not trade and status:
        trade = status.get("trade_idea")
    scores = {key: _num(scores_in.get(key)) for key in _SCORE_KEYS}
    scores["supported_prob"] = _pick_num(scores_in.get("supported_prob"), judge.get("supported_prob"))
    scores["judge_model"] = _pick_str(scores_in.get("judge_model"), judge.get("model")) or None
    try:
        files = sorted(p.name for p in run_dir.iterdir() if p.is_file())
    except OSError:
        files = []
    return {
        "folder": run_dir.name,
        "mission_id": _pick_str(manifest.get("mission_id")) or None,
        "hypothesis": _pick_str(manifest.get("hypothesis"), _read_text(run_dir / "hypothesis.txt")) or None,
        "status": _pick_str(manifest.get("status")) or None,
        "created_at": _pick_str(manifest.get("created_at")) or None,
        "manifest": manifest,
        "n_obs": _pick_num(stats.get("n_obs"), manifest.get("n_obs")),
        "coverage_start": _pick_str(stats.get("coverage_start")) or None,
        "coverage_end": _pick_str(stats.get("coverage_end")) or None,
        "pearson_r": _pick_num(corr.get("pearson_r"), manifest.get("r")),
        "spearman_r": _num(corr.get("spearman_r")),
        "best_lag": best_lag,
        "best_r": best_r,
        "perm_p": _pick_num(stats.get("perm_p"), manifest.get("perm_p")),
        "n_lags_tested": _num(stats.get("n_lags_tested")),
        "bonferroni_p": _num(stats.get("bonferroni_p")),
        "pre_post": stats.get("pre_post") if isinstance(stats.get("pre_post"), dict) else None,
        "window": _pick_str(stats.get("window")) or None,
        "scores": scores,
        "trade_idea": trade or None,
        "note_md": _read_text(run_dir / "note.md"),
        "has_viz": "viz.png" in files,
        "files": files,
    }


def _status_index(statuses: list[dict]) -> dict:
    by_id, by_folder = {}, {}
    for s in statuses or []:
        if s.get("mission_id"):
            by_id.setdefault(s["mission_id"], s)
        folder = s.get("run_folder") or ""
        if folder:
            by_folder.setdefault(Path(folder).name, s)
    return {"by_id": by_id, "by_folder": by_folder}


def _match_status(mission_id: str, folder: str, idx: dict) -> Optional[dict]:
    return idx["by_id"].get(mission_id) or idx["by_folder"].get(folder)


def _run_extra(path: Path) -> dict:
    """Extra per-folder fields beyond what ``kingdom.data.read_run`` returns."""
    manifest = _read_json(path / "manifest.json")
    stats = _read_json(path / "stats.json")
    judge = _read_json(path / "judge.json")
    scores_in = judge.get("scores") if isinstance(judge.get("scores"), dict) else {}
    best_lag, best_r = _best_lag(stats.get("lagged") if isinstance(stats.get("lagged"), dict) else {})
    pre_post = stats.get("pre_post") if isinstance(stats.get("pre_post"), dict) else {}
    trade = _read_json(path / "trade_idea.json")
    return {
        "best_lag": best_lag,
        "best_r": best_r,
        "bonferroni_p": _num(stats.get("bonferroni_p")),
        "n_lags_tested": _num(stats.get("n_lags_tested")),
        "pre_post_effect": _pick_num(pre_post.get("effect_size"), pre_post.get("cohens_d")),
        "actionability": _num(scores_in.get("actionability")),
        "supported_prob": _pick_num(scores_in.get("supported_prob"), judge.get("supported_prob")),
        "judge_model": _pick_str(scores_in.get("judge_model"), judge.get("model")) or None,
        "trade_idea": trade or None,
        "created_at": _pick_str(manifest.get("created_at")) or None,
    }


def build_runs(root: Path, results: dict, statuses: list[dict], cache: dict) -> list[dict]:
    """One dict per run folder, merged with results.csv and status files.

    ``cache`` is a caller-owned dict reused across refreshes; it holds the
    kingdom mtime cache plus a per-folder extra-read cache keyed on the
    manifest mtime so 200+ runs stay fast.
    """
    root = Path(root)
    runs_dir = root / "missions" / "runs"
    run_cache = cache.setdefault("runs", {})
    extra_cache = cache.setdefault("extra", {})
    missions = read_runs(runs_dir, index=read_index(runs_dir / "INDEX.md"), cache=run_cache)
    idx = _status_index(statuses)
    results = results or {}
    seen_extra = set()
    out = []
    for m in missions:
        try:
            manifest_mtime = (m.path / "manifest.json").stat().st_mtime
        except OSError:
            manifest_mtime = None
        extra = None
        if manifest_mtime is not None:
            cached = extra_cache.get(m.folder)
            if cached is not None and cached[0] == manifest_mtime:
                extra = cached[1]
        if extra is None:
            extra = _run_extra(m.path)
            if manifest_mtime is not None:
                extra_cache[m.folder] = (manifest_mtime, extra)
        seen_extra.add(m.folder)
        status_file = _match_status(m.mission_id, m.folder, idx) or {}
        status_scores = status_file.get("scores") if isinstance(status_file.get("scores"), dict) else {}
        row = results.get(m.mission_id) or results.get(m.folder) or {}
        actionability = _pick_num(
            extra.get("actionability"),
            row.get("actionability"),
            status_scores.get("actionability"),
        )
        trade = status_file.get("trade_idea") or extra.get("trade_idea")
        r = m.r
        effect = abs(r) if r is not None else extra.get("pre_post_effect")
        bonferroni_p = extra.get("bonferroni_p")
        created_at = extra.get("created_at") or _iso_from_ts(m.created_at)
        out.append({
            "folder": m.folder,
            "mission_id": m.mission_id or None,
            "hypothesis": m.hypothesis or None,
            "status": "failed" if m.failed else ("ok" if m.status == "ok" else m.status),
            "created_at": created_at,
            "n": m.n_obs,
            "r": r,
            "effect": effect,
            "best_lag": extra.get("best_lag"),
            "perm_p": m.perm_p,
            "bonferroni_p": bonferroni_p,
            "bonferroni_ok": bonferroni_p is not None and bonferroni_p < 0.05,
            "n_lags_tested": extra.get("n_lags_tested"),
            "validity": m.validity,
            "interestingness": m.interestingness,
            "unexpectedness": m.unexpectedness,
            "actionability": actionability,
            "supported_prob": extra.get("supported_prob"),
            "judge_model": extra.get("judge_model"),
            "signal": m.signal(),
            "trade_idea": trade or None,
            "agent_session_url": status_file.get("agent_session_url"),
            "brain_sessions": status_file.get("brain_sessions") or [],
            "has_viz": m.viz_path is not None,
            "has_note": m.note_path is not None,
        })
    for name in list(extra_cache):
        if name not in seen_extra:
            del extra_cache[name]
    return out


def leaderboard(runs: list[dict], limit: int = 25) -> list[dict]:
    ok = [r for r in runs if r.get("status") == "ok" and r.get("validity") is not None]
    ok.sort(key=lambda r: (-r["validity"], r["perm_p"] if r.get("perm_p") is not None else float("inf")))
    out = []
    for rank, r in enumerate(ok[:limit], start=1):
        out.append({
            "rank": rank,
            "mission_id": r.get("mission_id"),
            "folder": r.get("folder"),
            "hypothesis": r.get("hypothesis"),
            "validity": r.get("validity"),
            "effect": r.get("effect"),
            "n": r.get("n"),
            "perm_p": r.get("perm_p"),
            "bonferroni_ok": r.get("bonferroni_ok"),
            "actionability": r.get("actionability"),
            "trade_idea": r.get("trade_idea"),
        })
    return out


def git_head(root: Path) -> str:
    """``"<short sha> <branch>"`` for the repo, ``""`` on any failure."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    return f"{sha} {branch}".strip()


def git_pull(root: Path, timeout: float = 30) -> dict:
    """Run ``git pull --rebase --autostash``; never raises."""
    at = _iso_now()
    try:
        proc = subprocess.run(
            ["git", "pull", "--rebase", "--autostash"], cwd=root,
            capture_output=True, text=True, timeout=timeout,
        )
        output = (proc.stdout + proc.stderr).strip()
        return {"ok": proc.returncode == 0, "output": output, "at": at}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "output": str(exc), "at": at}


def diff_statuses(old: list[dict], new: list[dict], at: str) -> list[dict]:
    """Log events between two status snapshots, keyed on ``mission_id``."""
    old_by = {s.get("mission_id"): s for s in old or [] if s.get("mission_id")}
    new_by = {s.get("mission_id"): s for s in new or [] if s.get("mission_id")}
    events = []
    for mid, cur in new_by.items():
        prev = old_by.get(mid)
        if prev is None:
            events.append({
                "at": at, "mission_id": mid, "kind": "new",
                "field": None, "old": None, "new": cur.get("state"),
                "message": f"appeared ({cur.get('state')})",
            })
            continue
        for field in ("state", "stage", "progress", "message"):
            if prev.get(field) != cur.get(field):
                events.append({
                    "at": at, "mission_id": mid, "kind": "changed",
                    "field": field, "old": prev.get(field), "new": cur.get(field),
                    "message": cur.get("message"),
                })
    for mid in old_by:
        if mid not in new_by:
            events.append({
                "at": at, "mission_id": mid, "kind": "gone",
                "field": None, "old": old_by[mid].get("state"), "new": None,
                "message": "status file removed",
            })
    return events


class Monitor:
    """Thread-safe mission monitor; ``refresh()`` pulls git then re-reads disk."""

    def __init__(self, root: Path, pull_interval: float = 60.0, pull: bool = True):
        self.root = Path(root)
        self.pull_interval = float(pull_interval)
        self.pull = pull
        self._lock = threading.RLock()
        self._pull_lock = threading.Lock()
        self._state: Optional[dict] = None
        self._statuses: list[dict] = []
        self._cache: dict = {}
        self._log: list[dict] = []
        self._last_pull_at: float = 0.0
        self._pull: dict = {"ok": None, "output": "", "at": None}

    def refresh(self) -> dict:
        """Pull (if due) then rebuild state. The git pull runs under
        ``_pull_lock`` only, so ``state()``/``_lock`` readers never block
        on a slow pull."""
        if self.pull:
            with self._pull_lock:
                if time.time() - self._last_pull_at >= self.pull_interval:
                    pull = git_pull(self.root)
                    with self._lock:
                        self._pull = pull
                        self._last_pull_at = time.time()
        with self._lock:
            self._state = self._build(time.time())
            return self._state

    def _build(self, now: float) -> dict:
        missions = self.root / "missions"
        statuses = read_status_dir(missions / "status", now)
        queue = read_queue_entries(missions / "queue.txt")
        results = read_results_csv(missions / "results.csv")
        runs = build_runs(self.root, results, statuses, self._cache)
        failed_txt = read_failed(missions / "failed.txt")
        failed = [{"hypothesis": h, "error": e} for h, e in failed_txt]
        config = _read_json(missions / "config.json")
        head = git_head(self.root)
        head_sha, _, branch = head.partition(" ")
        at = _iso_now()
        events = diff_statuses(self._statuses, statuses, at)
        if events:
            self._log = (events + self._log)[:200]
        self._statuses = statuses
        counts = {
            "running": sum(1 for s in statuses if s["state"] == "running"),
            "queued": len(queue) + sum(1 for s in statuses if s["state"] == "queued"),
            "done": sum(1 for r in runs if r["status"] == "ok"),
            "failed": sum(1 for r in runs if r["status"] == "failed") + len(failed),
        }
        return {
            "generated_at": at,
            "generated_ts": now,
            "pull_interval": self.pull_interval,
            "pull_enabled": self.pull,
            "git": {
                "head": head_sha,
                "branch": branch,
                "last_pull_at": self._pull.get("at"),
                "last_pull_ok": self._pull.get("ok"),
                "pull_output": (self._pull.get("output") or "")[-400:],
            },
            "config": {"max_agents": _num(config.get("max_agents")) or 0},
            "counts": counts,
            "active": [s for s in statuses if s["state"] in ("running", "queued")],
            "statuses": statuses,
            "queue": queue,
            "runs": runs,
            "leaderboard": leaderboard(runs),
            "failed": failed,
            "log": self._log,
        }

    def state(self) -> dict:
        with self._lock:
            if self._state is None:
                return self.refresh()
            return self._state
