"""Round 2 mission progress files (missions/status/<mission_id>.json, see SCHEMA.md)."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from warsignal.config import ROOT

STATUS_DIR = ROOT / "missions" / "status"
QUEUE = ROOT / "missions" / "queue.txt"
STAGES = ["queued", "planning", "loading", "stats", "judging", "narrative", "viz", "trade", "followup", "publishing", "done"]
STATES = {"queued", "running", "done", "failed"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_path(mission_id):
    return STATUS_DIR / f"{mission_id}.json"


def read_status(mission_id):
    path = status_path(mission_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
        handle.write("\n")
    os.replace(tmp, path)


def new_status(mission_id, hypothesis, title=None, parent_mission_id=None, agent_session_url=None):
    return {
        "schema_version": 1,
        "mission_id": mission_id,
        "title": title or hypothesis[:80],
        "hypothesis": hypothesis,
        "parent_mission_id": parent_mission_id,
        "round": os.environ.get("WARSIGNAL_ROUND", "iran-round-2"),
        "agent_session_url": agent_session_url,
        "brain_sessions": [],
        "state": "queued",
        "stage": "queued",
        "progress": 0.0,
        "signal": None,
        "started_at": None,
        "updated_at": _now(),
        "finished_at": None,
        "elapsed_s": 0,
        "message": "queued",
        "run_folder": None,
        "scores": {"validity": None, "interestingness": None, "unexpectedness": None, "actionability": None},
        "trade_idea": None,
        "followup_hypothesis": None,
    }


def update_status(mission_id, **fields):
    """Merge ``fields`` into the status file (creating it if needed) and keep derived fields consistent."""
    current = read_status(mission_id) or new_status(mission_id, fields.get("hypothesis", ""))
    for key, value in fields.items():
        if value is None and key not in {"finished_at"}:
            continue
        if key == "scores" and isinstance(value, dict):
            current["scores"] = {**current.get("scores", {}), **value}
        else:
            current[key] = value
    if current["state"] not in STATES:
        raise ValueError(f"invalid state {current['state']!r}")
    if current["stage"] in STAGES:
        index = STAGES.index(current["stage"])
        current["progress"] = max(float(current.get("progress") or 0.0), round(index / 10, 2))
    if current["state"] == "running" and not current.get("started_at"):
        current["started_at"] = _now()
    if current["state"] in {"done", "failed"}:
        current["progress"] = 1.0
        current["finished_at"] = current.get("finished_at") or _now()
        if current["stage"] not in {"done"} and current["state"] == "done":
            current["stage"] = "done"
    scores = current.get("scores") or {}
    if current.get("signal") is None and scores.get("validity") is not None:
        current["signal"] = round(min(1.0, max(0.0, float(scores["validity"]) / 10)), 3)
    current["updated_at"] = _now()
    if current.get("started_at"):
        started = datetime.fromisoformat(current["started_at"].replace("Z", "+00:00"))
        current["elapsed_s"] = int((datetime.now(timezone.utc) - started).total_seconds())
    _atomic_write(status_path(mission_id), current)
    return current


def apply_result(mission_id, result):
    """Copy scores / trade idea / run folder from a finished MissionResult into the status file."""
    scores = {k: result.scores.get(k) for k in ("validity", "interestingness", "unexpectedness", "actionability")}
    run_folder = result.artifacts.get("run_folder")
    return update_status(
        mission_id,
        state="running" if result.status == "ok" else "failed",
        stage="trade" if result.status == "ok" else "done",
        scores=scores,
        trade_idea=result.trade_idea,
        run_folder=str(Path(run_folder).relative_to(ROOT)) if run_folder else None,
        message=result.error if result.status != "ok" else "analysis complete; writing follow-up",
        signal=(None if scores.get("validity") is None else round(min(1.0, scores["validity"] / 10), 3)),
    )


def append_followup(mission_id, text):
    """Append one `R2 | ... (parent: <id>)` line to the queue and record it in the status file."""
    line = text.strip()
    if not line.startswith("R2 |"):
        line = f"R2 | {line}"
    if "(parent:" not in line:
        line = f"{line} (parent: {mission_id})"
    existing = QUEUE.read_text(encoding="utf-8") if QUEUE.exists() else ""
    if line in existing.splitlines():
        return line
    with QUEUE.open("a", encoding="utf-8") as handle:
        if existing and not existing.endswith("\n"):
            handle.write("\n")
        handle.write(line + "\n")
    update_status(mission_id, followup_hypothesis=line)
    return line


def git_publish(paths, message, retries=3):
    """Stage only ``paths``, commit, pull --rebase --autostash, push. Never force."""
    paths = [str(p) for p in paths if Path(p).exists()]
    if not paths:
        return False
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return False
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    for _ in range(retries):
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=ROOT)
        if subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT).returncode == 0:
            return True
    print("status publish: push failed after retries", flush=True)
    return False


def publish_status(mission_id, extra_paths=(), message=None):
    paths = [status_path(mission_id), *extra_paths]
    return git_publish(paths, message or f"status {mission_id}: {(read_status(mission_id) or {}).get('state', '?')}")
