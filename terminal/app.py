"""Flask app for the WarSignal terminal UI."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from kingdom.data import _RUN_DIR
from warsignal.mission.monitor import Monitor, read_run_details

_STATE_MARKER = "window.__STATE__ = null;"


def index_html(state: dict | None = None) -> str:
    """Render ``index.html``; embed ``state`` for snapshot mode when given."""
    template = (Path(__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")
    if state is None:
        return template
    blob = json.dumps(state).replace("</", "<\\/")
    return template.replace(_STATE_MARKER, f"window.__STATE__ = {blob};", 1)


def _run_dir(monitor: Monitor, folder: str) -> Path | None:
    if not _RUN_DIR.match(folder or ""):
        return None
    runs_dir = (monitor.root / "missions" / "runs").resolve()
    target = (runs_dir / folder).resolve()
    if not target.is_dir() or target.parent != runs_dir:
        return None
    return target


def create_app(monitor: Monitor) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return index_html()

    @app.get("/api/state")
    def api_state():
        if request.args.get("refresh") == "1":
            monitor.refresh()
        return jsonify(monitor.state())

    @app.get("/api/run/<folder>")
    def api_run(folder):
        target = _run_dir(monitor, folder)
        if target is None:
            abort(404)
        status = next(
            (s for s in monitor.state().get("statuses", [])
             if Path(s.get("run_folder") or "").name == folder),
            None,
        )
        return jsonify(read_run_details(target, status))

    @app.get("/runs/<folder>/<file>")
    def run_file(folder, file):
        target = _run_dir(monitor, folder)
        if target is None or not file or "/" in file or ".." in file:
            abort(404)
        path = (target / file).resolve()
        if path.parent != target or not path.is_file():
            abort(404)
        return send_from_directory(target, file)

    @app.get("/snapshot")
    def snapshot():
        return index_html(monitor.state())

    return app


def start_refresh_thread(monitor: Monitor) -> threading.Thread:
    """Background daemon that refreshes (git pull + reload) on the interval."""
    def loop():
        while True:
            try:
                monitor.refresh()
            except Exception:
                pass
            time.sleep(max(1.0, monitor.pull_interval))

    thread = threading.Thread(target=loop, daemon=True, name="terminal-refresh")
    thread.start()
    return thread
