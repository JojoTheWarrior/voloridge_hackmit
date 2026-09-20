from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from warsignal.config import ROOT
from .naming import folder_name, next_counter

log = logging.getLogger(__name__)

GRAPHS_DIR = ROOT / "graphs"


class RenderError(RuntimeError):
    pass


def create_folder(chart_type: str, indicators: list[str]) -> Path:
    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    counter = next_counter(GRAPHS_DIR)
    folder = GRAPHS_DIR / folder_name(date.today(), counter, chart_type, indicators)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def render_thumbnail(folder: Path, timeout: int = 90) -> Path:
    env = dict(os.environ)
    env.update({"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy", "CHART_HEADLESS": "thumbnail.png"})
    try:
        proc = subprocess.run([sys.executable, "chart.py"], cwd=folder, env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RenderError(f"chart render timed out after {timeout}s") from exc
    target = folder / "thumbnail.png"
    if proc.returncode != 0:
        raise RenderError((proc.stderr or proc.stdout or "render failed")[-2000:])
    if not target.exists():
        raise RenderError("chart.py exited 0 but thumbnail.png was not created")
    return target


def write_readme(folder: Path, prompt: str, plan: dict, series: list[dict]) -> Path:
    lines = [f"# {plan.get('title', folder.name)}", "",
             f"- prompt: {prompt}", f"- chart_type: {plan.get('chart_type')}",
             f"- codegen: {plan.get('codegen', 'unknown')}",
             f"- folder: {folder.name}", "", "## Series", ""]
    for s in series:
        lines.append(f"- `{s.get('indicator', s['file'])}` — {s.get('label', '')} "
                     f"({s.get('start', '?')}..{s.get('end', '?')}, n={s.get('rows', '?')})")
    if plan.get("notes"):
        lines += ["", f"Notes: {plan['notes']}"]
    if plan.get("rationale"):
        lines += [f"Rationale: {plan['rationale']}"]
    lines += ["", "Files: `plan.json`, `prompt.txt`, `chart.py`, `data/*.csv`, `iran_timeline.csv`, `thumbnail.png`."]
    path = folder / "README.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def update_index(graphs_dir: Path = GRAPHS_DIR) -> Path:
    rows = []
    if graphs_dir.exists():
        for folder in sorted(graphs_dir.iterdir(), reverse=True):
            if not folder.is_dir() or not re.match(r"^\d{8}-\d{3}-", folder.name):
                continue
            prompt, chart_type, indicators = "", folder.name.split("-", 3)[-1], ""
            prompt_file = folder / "prompt.txt"
            plan_file = folder / "plan.json"
            if prompt_file.exists():
                prompt = prompt_file.read_text(encoding="utf-8").strip().replace("|", "\\|")
            if plan_file.exists():
                try:
                    plan = json.loads(plan_file.read_text(encoding="utf-8"))
                    chart_type = plan.get("chart_type", chart_type)
                    indicators = ", ".join(plan.get("indicators", []))
                except Exception:
                    pass
            day = f"{folder.name[:4]}-{folder.name[4:6]}-{folder.name[6:8]}"
            rows.append(f"| [{folder.name}]({folder.name}/) | {day} | {chart_type} | {indicators} | {prompt} |")
    content = "# WarSignal graphs\n\n| Folder | Date | Type | Indicators | Prompt |\n| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    path = graphs_dir / "INDEX.md"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def git_commit_push(folder: Path, counter: int, slug: str, branch: str = "graph-ui") -> dict:
    if os.environ.get("WARSIGNAL_GRAPH_NO_GIT") == "1":
        return {"committed": False, "pushed": False, "error": None}
    result = {"committed": False, "pushed": False, "error": None}
    try:
        subprocess.run(["git", "add", f"graphs/{folder.name}", "graphs/INDEX.md"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", f"graph {counter:03d}: {slug}"],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        result["committed"] = True
        subprocess.run(["git", "push", "origin", branch], cwd=ROOT, check=True,
                       capture_output=True, text=True)
        result["pushed"] = True
    except subprocess.CalledProcessError as exc:
        result["error"] = (exc.stderr or str(exc))[-500:]
        log.warning("graph git step failed: %s", result["error"])
    except Exception as exc:
        result["error"] = str(exc)
        log.warning("graph git step failed: %s", exc)
    return result
