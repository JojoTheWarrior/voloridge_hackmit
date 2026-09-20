from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from warsignal.indicators import list_indicators
from warsignal.mission.harness import run_queue
from warsignal.mission.results import append_result, load_results
from warsignal.mission.runner import run_mission

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "missions" / "reports"


def _page():
    examples = [spec.name for spec in list_indicators()[:20]]
    page = """<!doctype html>
<html><head><meta charset="utf-8"><title>WarSignal</title>
<style>
body{margin:0;background:#0f1117;color:#e2e8f0;font:14px system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:24px}textarea{width:100%;height:72px;background:#171b25;color:#fff;border:1px solid #3b4557;border-radius:6px;padding:10px}
button{background:#4cc9f0;color:#081018;border:0;border-radius:5px;padding:9px 14px;margin:8px 4px 8px 0;cursor:pointer}
.card{background:#171b25;border:1px solid #2a2f3a;border-radius:8px;padding:16px;margin-top:16px}
.scores{display:flex;gap:18px}.score{width:30%;background:#2a2f3a;height:20px}.score i{display:block;background:#f72585;height:100%}
table{width:100%;border-collapse:collapse}td,th{padding:7px;border-bottom:1px solid #2a2f3a;text-align:left}img{max-width:1000px}
pre{white-space:pre-wrap;color:#cbd5e1}.hint{color:#94a3b8;font-size:12px}
</style></head><body><main>
<h1>WarSignal</h1><p class="hint">Alternative-data hypothesis lab for the Iran war.</p>
<textarea id="hypothesis" placeholder="Type a hypothesis"></textarea>
<div class="hint">Examples: {{EXAMPLES}}</div>
<button onclick="runMission()">Run</button><button onclick="runNext()">Pop &amp; run next queued mission</button>
<span id="queue"></span><div id="result"></div><div class="card"><h2>Past missions</h2><div id="past"></div></div>
<script>
async function refresh(){let r=await fetch('/api/results');let x=await r.json();document.getElementById('past').innerHTML='<table><tr><th>Mission</th><th>Interest</th><th>Unexpected</th><th>Status</th></tr>'+x.map(a=>'<tr><td>'+a.mission_id+'</td><td>'+a.interestingness+'</td><td>'+a.unexpectedness+'</td><td>'+a.status+'</td></tr>').join('')+'</table>';let q=await fetch('/api/queue');document.getElementById('queue').textContent=' Queue length: '+(await q.json()).length}
async function runMission(){let box=document.getElementById('result');box.innerHTML='<div class="card">Running mission…</div>';let r=await fetch('/api/mission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hypothesis:document.getElementById('hypothesis').value})});let x=await r.json();box.innerHTML=render(x)}
async function runNext(){let r=await fetch('/api/queue/next',{method:'POST'});let x=await r.json();document.getElementById('result').innerHTML=render(x);refresh()}
function render(x){if(x.error)return '<div class="card"><pre>'+x.error+'</pre></div>';let s=x.scores||{};return '<div class="card"><h2>'+x.mission_id+'</h2><div class="scores">'+['validity','interestingness','unexpectedness'].map(k=>'<div>'+k+' '+s[k]+'<div class="score"><i style="width:'+(10*s[k])+'%"></i></div></div>').join('')+'</div><p>'+x.narrative_md+'</p>'+(x.artifacts.viz_path?'<img src="/reports/'+x.mission_id+'.png">':'')+'<p><a href="/reports/'+x.mission_id+'.md">report</a> <a href="/reports/'+x.mission_id+'.json">json</a> <button onclick="fetch(\\'/api/show/'+x.mission_id+'\\',{method:\\'POST\\'})">Open interactive Pygame window</button></p><pre>'+JSON.stringify(x.stats,null,2)+'</pre></div>'}
refresh()
</script></main></body></html>"""
    return page.replace("{{EXAMPLES}}", ", ".join(examples))


def _result_json(result):
    data = dict(result.__dict__)
    data["plan"] = result.plan.__dict__
    return data


def create_app():
    app = Flask(__name__)

    @app.get("/")
    def index():
        return _page()

    @app.get("/api/indicators")
    def indicators():
        return jsonify([spec.name for spec in list_indicators()])

    @app.get("/api/results")
    def results():
        rows = load_results()
        rows.sort(key=lambda row: (float(row.get("interestingness") or 0), float(row.get("unexpectedness") or 0)), reverse=True)
        return jsonify(rows)

    @app.get("/api/queue")
    def queue():
        path = ROOT / "missions" / "queue.txt"
        return jsonify([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else [])

    @app.post("/api/mission")
    def mission():
        body = request.get_json(silent=True) or {}
        hypothesis = str(body.get("hypothesis", "")).strip()
        if not hypothesis:
            return jsonify({"error": "hypothesis is required"}), 400
        result = run_mission(hypothesis, viz=True)
        append_result(result)
        return jsonify(_result_json(result))

    @app.post("/api/queue/next")
    def next_mission():
        results = run_queue(1, viz=True)
        if not results:
            return jsonify({"error": "queue is empty"}), 404
        result = results[0]
        return jsonify(_result_json(result))

    @app.post("/api/show/<mission_id>")
    def show(mission_id):
        subprocess.Popen([sys.executable, "main.py", "viz", mission_id], cwd=ROOT)
        return jsonify({"started": True, "mission_id": mission_id})

    @app.get("/reports/<path:name>")
    def report(name):
        return send_from_directory(REPORTS, name)

    return app
