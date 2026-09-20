"""Single-window pygame chart launcher. POST /run {folder, script} replaces the running chart."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GRAPHS_DIR = ROOT / "graphs"

STATE = {"proc": None, "folder": None, "script": None, "started": None}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/status":
            proc = STATE["proc"]
            self._send(200, {"running": bool(proc and proc.poll() is None), "pid": proc.pid if proc else None,
                             "folder": STATE["folder"], "started": STATE["started"]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except Exception:
            self._send(400, {"error": "invalid json"})
            return
        folder = Path(body.get("folder", "")).resolve()
        script = body.get("script", "chart.py")
        try:
            inside = folder.is_relative_to(GRAPHS_DIR.resolve())
        except AttributeError:
            inside = str(folder).startswith(str(GRAPHS_DIR.resolve()))
        if not inside or not folder.is_dir():
            self._send(400, {"error": "folder must be inside graphs/"})
            return
        script_path = folder / script
        if not script_path.exists():
            script_path = folder / "_posted_chart.py"
            script_path.write_text(script, encoding="utf-8")
        proc = STATE["proc"]
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        STATE["proc"] = subprocess.Popen([sys.executable, script_path.name], cwd=folder)
        STATE["folder"], STATE["script"] = str(folder), script_path.name
        STATE["started"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self._send(200, {"pid": STATE["proc"].pid, "folder": str(folder), "script": script_path.name})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    print(f"charts launcher on http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
