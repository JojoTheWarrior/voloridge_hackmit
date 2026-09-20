from __future__ import annotations

import logging
import shutil
import threading
import time
import traceback
from pathlib import Path

from warsignal.config import DATA_REF
from . import cache, store
from .agent import collect_data, fetch_external, generate_chart, plan_request
from .chart_template import CHART_TEMPLATE
from .store import GRAPHS_DIR
from .validator import validate_script

log = logging.getLogger(__name__)


class GraphService:
    def __init__(self, charts_url: str = "http://127.0.0.1:8011"):
        self.charts_url = charts_url
        self.history: list[dict] = []
        self._lock = threading.Lock()
        self._counter = 0

    def submit(self, prompt: str) -> dict:
        with self._lock:
            self._counter += 1
            job = {"id": f"g{self._counter:04d}", "prompt": prompt, "status": "queued",
                   "folder": None, "indicators": [], "chart_type": None, "error": None,
                   "created": time.strftime("%Y-%m-%d %H:%M:%S"), "cached_from": None}
            self.history.insert(0, job)
        thread = threading.Thread(target=self._run, args=(job,), daemon=True)
        thread.start()
        return job

    def _set(self, job: dict, status: str, **fields):
        with self._lock:
            job["status"] = status
            job.update(fields)

    def _run(self, job: dict):
        prompt = job["prompt"]
        try:
            hit = cache.find_match(prompt, GRAPHS_DIR, confirm=cache.llm_confirm)
            if hit:
                folder = GRAPHS_DIR / hit["folder"]
                self._set(job, "cached", folder=hit["folder"], cached_from=hit["folder"],
                          chart_type=hit["plan"].get("chart_type"),
                          indicators=hit["plan"].get("indicators", []))
                if not hit["plan"].get("external"):
                    try:
                        stale = any(time.time() - f.stat().st_mtime > 86400
                                    for f in (folder / "data").glob("*.csv"))
                        if stale:
                            collect_data(hit["plan"], folder / "data")
                    except Exception as exc:
                        log.warning("cache refresh failed for %s: %s", hit["folder"], exc)
                self.launch(folder)
                return

            self._set(job, "planning")
            plan = plan_request(prompt)
            self._set(job, "planning", indicators=plan.get("indicators", []),
                      chart_type=plan.get("chart_type"))
            folder = store.create_folder(plan.get("chart_type", "line"), plan.get("indicators", []))
            self._set(job, "fetching", folder=folder.name)
            (folder / "prompt.txt").write_text(prompt, encoding="utf-8")
            timeline = DATA_REF / "iran_timeline.csv"
            if timeline.exists():
                shutil.copy(timeline, folder / "iran_timeline.csv")

            series = collect_data(plan, folder / "data")
            notes = [s.get("source_note") for s in series if s.get("source_note")]
            for item in plan.get("external", []):
                try:
                    ext = fetch_external(item, folder / "data")
                    series.append(ext)
                    notes.append(ext.get("source_note"))
                except Exception as exc:
                    log.warning("external fetch failed for %s: %s", item, exc)
            plan["series"] = [{"file": s["file"], "label": s["label"],
                               "indicator": s["indicator"]} for s in series]
            if plan.get("chart_type") == "scatter" and len(series) >= 2:
                plan.setdefault("x_series", series[0]["file"])
                plan.setdefault("y_series", series[1]["file"])
            plan["source_notes"] = [n for n in notes if n]
            import json
            (folder / "plan.json").write_text(json.dumps(plan, indent=2, default=str), encoding="utf-8")

            self._set(job, "codegen")
            source = generate_chart(plan, series)
            errors = validate_script(source)
            if errors:
                source = generate_chart(plan, series, feedback="; ".join(errors))
                errors = validate_script(source)
            if errors:
                log.warning("generated chart still invalid (%s); using template", errors)
                source = CHART_TEMPLATE
            (folder / "chart.py").write_text(source, encoding="utf-8")

            self._set(job, "rendering")
            try:
                store.render_thumbnail(folder)
            except store.RenderError as exc:
                repaired = generate_chart(plan, series, feedback=str(exc))
                if validate_script(repaired):
                    repaired = CHART_TEMPLATE
                (folder / "chart.py").write_text(repaired, encoding="utf-8")
                try:
                    store.render_thumbnail(folder)
                except store.RenderError as exc2:
                    self._set(job, "error", error=f"render failed: {exc2}")
                    return

            self._set(job, "saving")
            store.write_readme(folder, prompt, plan, series)
            store.update_index(GRAPHS_DIR)
            slug = folder.name.split("-", 3)[-1]
            counter = int(folder.name.split("-")[1]) if folder.name.split("-")[1].isdigit() else 0
            git = store.git_commit_push(folder, counter, slug)
            self.launch(folder)
            self._set(job, "done", error=git.get("error"))
        except Exception as exc:
            log.error("graph job failed: %s\n%s", exc, traceback.format_exc())
            self._set(job, "error", error=str(exc))

    def launch(self, folder: Path):
        try:
            import requests
            requests.post(self.charts_url + "/run",
                          json={"folder": str(folder), "script": "chart.py"}, timeout=5)
        except Exception as exc:
            log.warning("charts launcher unavailable: %s", exc)

    def history_view(self) -> list[dict]:
        with self._lock:
            jobs = [dict(j) for j in self.history]
        known = {j["folder"] for j in jobs if j.get("folder")}
        if GRAPHS_DIR.exists():
            import json
            for folder in sorted(GRAPHS_DIR.iterdir(), reverse=True):
                if not folder.is_dir() or folder.name in known:
                    continue
                prompt_file, plan_file = folder / "prompt.txt", folder / "plan.json"
                if not prompt_file.exists():
                    continue
                plan = {}
                if plan_file.exists():
                    try:
                        plan = json.loads(plan_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                jobs.append({"id": folder.name, "prompt": prompt_file.read_text(encoding="utf-8").strip(),
                             "status": "done", "folder": folder.name,
                             "indicators": plan.get("indicators", []),
                             "chart_type": plan.get("chart_type"), "error": None,
                             "created": folder.name[:8], "cached_from": None})
        return jobs
