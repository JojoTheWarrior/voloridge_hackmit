from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from warsignal.indicators import list_indicators
from warsignal.mission.harness import run_queue
from warsignal.mission.results import append_result, load_results
from warsignal.mission.runner import run_mission
from warsignal.util import to_jsonable

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "missions" / "reports"


def _page():
    preferred = [
        "gdelt.irn.events", "gdelt.gkg.hormuz_share", "weather.tehran.temp_anomaly",
        "airquality.houston.pm25", "research.helium.pubs", "materials.docs_updated",
        "utility.us.demand_anomaly", "finance.BZ=F.log_return", "events.hormuz.count",
    ]
    available = {spec.name for spec in list_indicators()}
    examples = [name for name in preferred if name in available]
    examples.extend(spec.name for spec in list_indicators() if spec.name not in examples and len(examples) < 20)
    page = """<!doctype html>
<html><head><meta charset="utf-8"><title>WarSignal</title>
<style>
body{margin:0;background:#0f1117;color:#e2e8f0;font:14px system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:24px}textarea{width:100%;height:72px;background:#171b25;color:#fff;border:1px solid #3b4557;border-radius:6px;padding:10px}
button{background:#4cc9f0;color:#081018;border:0;border-radius:5px;padding:9px 14px;margin:8px 4px 8px 0;cursor:pointer}
.card{background:#171b25;border:1px solid #2a2f3a;border-radius:8px;padding:16px;margin-top:16px}
.scores{display:flex;gap:18px}.score{width:30%;background:#2a2f3a;height:20px}.score i{display:block;background:#f72585;height:100%}
table{width:100%;border-collapse:collapse}td,th{padding:7px;border-bottom:1px solid #2a2f3a;text-align:left}tr[data-id]{cursor:pointer}tr[data-id]:hover{background:#202635}img{max-width:1000px}
pre{white-space:pre-wrap;color:#cbd5e1}.hint{color:#94a3b8;font-size:12px}
</style></head><body><main>
<h1>WarSignal</h1><p class="hint">Alternative-data hypothesis lab for the Iran war.</p>
<textarea id="hypothesis" placeholder="Type a hypothesis"></textarea>
<div class="hint">Indicators: {{EXAMPLES}}</div>
<div class="hint">Example hypotheses:
<button onclick="fillExample(0)">News leads Brent</button>
<button onclick="fillExample(1)">Weather and air quality</button>
<button onclick="fillExample(2)">Demand and gas</button></div>
<button onclick="runMission()">Run</button><button onclick="runNext()">Pop &amp; run next queued mission</button>
<span id="queue"></span><div id="result"></div><div class="card"><h2>Past missions</h2>
<button onclick="refresh('interestingness')">Sort by interestingness</button><button onclick="refresh('unexpectedness')">Sort by unexpectedness</button>
<div id="past"></div></div>
<script>
const examples=[
"GDELT Iran news volume leads Brent crude daily returns by 1-3 days around the war.",
"Higher Tehran wind speed coincides with lower Houston PM2.5 during the war.",
"US electricity demand anomaly correlates with Henry Hub natural gas returns during the war."
];
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function fillExample(i){document.getElementById('hypothesis').value=examples[i]}
async function refresh(sort='interestingness'){let r=await fetch('/api/results');let x=await r.json();x.sort((a,b)=>(parseFloat(b[sort]||0)-parseFloat(a[sort]||0))||(parseFloat(b.unexpectedness||0)-parseFloat(a.unexpectedness||0)));document.getElementById('past').innerHTML='<table><tr><th>Mission</th><th>Hypothesis</th><th>Validity</th><th>n</th><th>r</th><th>Reports</th></tr>'+x.map(a=>'<tr data-id="'+esc(a.mission_id)+'" onclick="selectPast(\\''+esc(a.mission_id)+'\\')"><td>'+esc(a.mission_id)+'</td><td>'+esc((a.hypothesis||'').slice(0,90))+'</td><td>'+esc(a.validity)+'</td><td>'+esc(a.n_obs)+'</td><td>'+esc(a.pearson_r)+'</td><td><a href="/reports/'+esc(a.mission_id)+'.md" onclick="event.stopPropagation()">md</a> <a href="/reports/'+esc(a.mission_id)+'.png" onclick="event.stopPropagation()">png</a></td></tr>').join('')+'</table>';let q=await fetch('/api/queue');document.getElementById('queue').textContent=' Queue length: '+(await q.json()).length}
async function runMission(){let box=document.getElementById('result');box.innerHTML='<div class="card">Running mission… please wait</div>';let r=await fetch('/api/mission',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hypothesis:document.getElementById('hypothesis').value})});let x=await r.json();box.innerHTML=render(x);refresh()}
async function runNext(){let r=await fetch('/api/queue/next',{method:'POST'});let x=await r.json();document.getElementById('result').innerHTML=render(x);refresh()}
async function selectPast(id){let r=await fetch('/api/results/'+encodeURIComponent(id));let x=await r.json();document.getElementById('result').innerHTML=render(x)}
function render(x){if(x.error)return '<div class="card"><pre>'+esc(x.error)+'</pre></div>';let s=x.scores||{};return '<div class="card"><h2>'+esc(x.mission_id)+'</h2><div class="scores">'+['validity','interestingness','unexpectedness'].map(k=>'<div>'+k+' '+esc(s[k])+'<div class="score"><i style="width:'+(10*(s[k]||0))+'%"></i></div></div>').join('')+'</div><p><b>n='+esc(x.n_obs)+'</b> r='+esc((x.stats?.correlation||{}).pearson_r)+'</p><pre>'+esc(x.narrative_md||'')+'</pre>'+(x.artifacts?.viz_path?'<img src="/reports/'+esc(x.mission_id)+'.png">':'')+'<p><a href="/reports/'+esc(x.mission_id)+'.md">report</a> <a href="/reports/'+esc(x.mission_id)+'.json">json</a> <button onclick="fetch(\\'/api/show/'+esc(x.mission_id)+'\\',{method:\\'POST\\'})">Open interactive Pygame window</button></p><pre>'+esc(JSON.stringify(x.stats||{},null,2))+'</pre></div>'}
refresh()
</script></main></body></html>"""
    return page.replace("{{EXAMPLES}}", ", ".join(examples))


def _result_json(result):
    data = dict(result.__dict__)
    data["plan"] = result.plan.__dict__
    return to_jsonable(data)


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

    @app.get("/api/results/<mission_id>")
    def result_detail(mission_id):
        path = REPORTS / f"{mission_id}.json"
        if not path.exists():
            return jsonify({"error": "mission not found"}), 404
        return jsonify(to_jsonable(__import__("json").loads(path.read_text(encoding="utf-8"))))

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
