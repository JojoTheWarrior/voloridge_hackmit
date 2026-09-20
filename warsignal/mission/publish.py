"""Persist self-contained mission runs and optionally publish them."""

from __future__ import annotations

import fcntl
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from warsignal.indicators import REGISTRY
from warsignal.util import to_jsonable


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "missions" / "runs"
LOCK = RUNS / ".lock"


def _slug(value: str, limit: int = 40) -> str:
    value = value.replace(".", "-").replace("=F", "-f").replace("^", "")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:limit].rstrip("-") or "unknown"


def _failed_slug(hypothesis: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", hypothesis)[:5]
    return "FAILED-" + (_slug("-".join(words)) or "mission")


def _next_folder(result) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        numbers = [
            int(match.group(1))
            for path in RUNS.iterdir()
            if (match := re.match(r"^\d{8}-(\d{3})-", path.name))
        ]
        number = max(numbers, default=0) + 1
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        if result.status == "ok":
            suffix = (
                f"{_slug(result.plan.indicator_a)}_prepost"
                if result.plan.mode == "single"
                else f"{_slug(result.plan.indicator_a)}_x_{_slug(result.plan.indicator_b)}"
            )
        else:
            suffix = _failed_slug(result.hypothesis)
        folder = RUNS / f"{date}-{number:03d}-{suffix}"
        folder.mkdir()
        fcntl.flock(handle, fcntl.LOCK_UN)
    return folder


def _coverage(name: str) -> str:
    spec = REGISTRY.get(name)
    return spec.coverage if spec else ""


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _write_index():
    rows = []
    for folder in sorted(RUNS.iterdir()):
        if not folder.is_dir() or not re.match(r"^\d{8}-\d{3}-", folder.name):
            continue
        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows.append(manifest)
    lines = [
        "# Mission Runs",
        "",
        "| Folder | Hypothesis | Status | n | r | perm_p | Validity | Interest | Unexpected | Brain |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        hypothesis = str(row.get("hypothesis", "")).replace("|", "\\|").replace("\n", " ")
        brain = "<br>".join(
            "[{}]({})".format(item.get("purpose", "brain"), item["session_url"])
            for item in row.get("brain_sessions", [])
            if item.get("session_url")
        )
        lines.append(
            f"| `{row['folder']}` | {hypothesis} | {row.get('status', '')} | "
            f"{row.get('n_obs', '')} | {row.get('r', '')} | {row.get('perm_p', '')} | "
            f"{row.get('validity', '')} | {row.get('interestingness', '')} | "
            f"{row.get('unexpectedness', '')} | {brain} |"
        )
    (RUNS / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_folder(result, raw_a=None, raw_b=None, transformed_a=None, transformed_b=None, judge=None):
    """Write a complete, reproducible folder and return its path."""
    folder = _next_folder(result)
    (folder / "data").mkdir()
    (folder / "hypothesis.txt").write_text(result.hypothesis + "\n", encoding="utf-8")
    (folder / "plan.json").write_text(
        json.dumps(to_jsonable(result.plan.__dict__), indent=2) + "\n", encoding="utf-8"
    )
    (folder / "stats.json").write_text(
        json.dumps(to_jsonable(result.stats), indent=2) + "\n", encoding="utf-8"
    )
    judge_payload = dict(judge or {})
    judge_payload.setdefault("scores", result.scores)
    judge_payload.setdefault("judge", result.judge)
    judge_payload.setdefault("model", result.scores.get("judge_model", ""))
    judge_payload.setdefault("confidence", {})
    judge_payload.setdefault("raw", {})
    (folder / "judge.json").write_text(
        json.dumps(to_jsonable(judge_payload), indent=2) + "\n", encoding="utf-8"
    )
    indicator_table = f"`{result.plan.indicator_a}`"
    source_table = f"`{result.plan.indicator_a}` ({_coverage(result.plan.indicator_a)})"
    if result.plan.mode != "single":
        indicator_table += f" × `{result.plan.indicator_b}`"
        source_table += f"; `{result.plan.indicator_b}` ({_coverage(result.plan.indicator_b)})"
    correlation = (result.stats.get("correlation") or {}).get("pearson_r")
    lag = (result.stats.get("lagged") or {}).get("best_lag")
    pre_post = result.stats.get("pre_post") or {}
    change_label = "pre/post mean Δ" if result.plan.mode == "single" else "pre/post Δr"
    change_value = pre_post.get("mean_diff") if result.plan.mode == "single" else pre_post.get("r_change")
    test_label = "Welch p" if result.plan.mode == "single" else "Fisher p"
    test_value = pre_post.get("welch_p") if result.plan.mode == "single" else pre_post.get("fisher_z_p")
    note = (
        f"# {result.mission_id}\n\n"
        "| Field | Value |\n|---|---|\n"
        f"| Mission id | `{result.mission_id}` |\n| Folder | `{folder.name}` |\n"
        f"| Indicators | {indicator_table} |\n"
        f"| n_obs | {result.n_obs} |\n"
        f"| r | {'' if correlation is None else correlation} |\n"
        f"| Best lag | {('n/a' if lag is None else lag)} ({result.stats.get('lag_unit', 'days')}) |\n"
        f"| perm_p | {result.stats.get('perm_p')} |\n| Bonferroni | {result.stats.get('bonferroni_p')} |\n"
        f"| {change_label} | {'' if change_value is None else change_value} |\n"
        f"| {test_label} | {'' if test_value is None else test_value} |\n"
        f"| Scores | {result.scores} |\n"
        f"| Data sources | {source_table} |\n\n"
        f"{result.narrative_md or result.error or ''}\n"
    )
    (folder / "note.md").write_text(note, encoding="utf-8")
    raw_series = [("raw_a.csv", raw_a)]
    if result.plan.mode != "single":
        raw_series.append(("raw_b.csv", raw_b))
    for path, series in raw_series:
        frame = pd.Series(series, dtype="float64") if series is not None else pd.Series(dtype="float64")
        frame.to_csv(folder / "data" / path, index_label="date", header=["value"])
    if result.plan.mode == "single":
        aligned = pd.DataFrame({"value": transformed_a}).dropna()
    else:
        aligned = pd.DataFrame({"a": transformed_a, "b": transformed_b}).dropna() if transformed_a is not None and transformed_b is not None else pd.DataFrame(columns=["a", "b"])
    aligned.to_csv(folder / "data" / "aligned.csv", index_label="date")
    manifest = {
        "created_at": result.created_at,
        "git_commit": _git_commit(),
        "folder": folder.name,
        "mission_id": result.mission_id,
        "hypothesis": result.hypothesis,
        "status": result.status,
        "n_obs": result.n_obs,
        "r": (result.stats.get("correlation") or {}).get("pearson_r"),
        "perm_p": result.stats.get("perm_p"),
        "validity": result.scores.get("validity"),
        "interestingness": result.scores.get("interestingness"),
        "unexpectedness": result.scores.get("unexpectedness"),
        "brain_sessions": result.brain_sessions,
        "indicator_coverage": {
            result.plan.indicator_a: _coverage(result.plan.indicator_a),
            **({} if result.plan.mode == "single" else {
                result.plan.indicator_b: _coverage(result.plan.indicator_b),
            }),
        },
        "versions": {
            "python": platform.python_version(),
            "pandas": importlib.metadata.version("pandas"),
            "numpy": importlib.metadata.version("numpy"),
        },
    }
    (folder / "manifest.json").write_text(json.dumps(to_jsonable(manifest), indent=2) + "\n", encoding="utf-8")
    with LOCK.open("a+", encoding="utf-8"):
        _write_index()
    return folder


def publish_run(folder):
    """Commit a run folder and index, then push when explicitly requested."""
    folder = Path(folder)
    subprocess.run(["git", "add", str(folder), str(RUNS / "INDEX.md")], cwd=ROOT, check=True)
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if staged.returncode == 0:
        return False
    mission_id = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))["mission_id"]
    slug = folder.name.split("-", 2)[-1]
    subprocess.run(["git", "commit", "-m", f"mission {mission_id}: {slug}"], cwd=ROOT, check=True)
    push = subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT)
    if push.returncode:
        print("mission publish push failed; retrying after git pull --rebase", flush=True)
        pull = subprocess.run(["git", "pull", "--rebase"], cwd=ROOT)
        if pull.returncode == 0:
            subprocess.run(["git", "push", "origin", "HEAD"], cwd=ROOT)
        else:
            print("mission publish pull --rebase failed; continuing", flush=True)
    return True
