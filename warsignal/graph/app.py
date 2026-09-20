from __future__ import annotations

from flask import Flask, jsonify, request, send_from_directory

from .store import GRAPHS_DIR

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>WarSignal Graphs</title>
<style>
body{margin:0;background:#0f1117;color:#e2e8f0;font:14px system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:24px}input{width:100%;background:#171b25;color:#fff;border:1px solid #3b4557;border-radius:6px;padding:10px;box-sizing:border-box}
button{background:#4cc9f0;color:#081018;border:0;border-radius:5px;padding:9px 14px;margin:8px 4px 8px 0;cursor:pointer}
.card{background:#171b25;border:1px solid #2a2f3a;border-radius:8px;padding:16px;margin-top:16px}
table{width:100%;border-collapse:collapse}td,th{padding:7px;border-bottom:1px solid #2a2f3a;text-align:left}
img.thumb{max-width:220px;border-radius:4px}.hint{color:#94a3b8;font-size:12px}a{color:#4cc9f0}
</style></head><body><main>
<h1>WarSignal Graph Reels</h1><p class="hint">Natural language &rarr; pygame chart. Each request is saved under graphs/ and launched in the charts window.</p>
<input id="prompt" placeholder="e.g. the instagram reels of the price of brent">
<button onclick="run()">Run</button>
<div class="card"><h2>History</h2><div id="past"></div></div>
<script>
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function refresh(){
let r=await fetch('/api/history');let x=await r.json();
document.getElementById('past').innerHTML='<table><tr><th>Status</th><th>Prompt</th><th>Type</th><th>Indicators</th><th>Chart</th><th></th></tr>'+x.map(j=>{
let links=j.folder?'<a href="/graphs/'+esc(j.folder)+'/README.md">readme</a> <a href="/graphs/'+esc(j.folder)+'/chart.py">chart.py</a> <a href="/graphs/'+esc(j.folder)+'/plan.json">plan</a> <a href="/graphs/'+esc(j.folder)+'/thumbnail.png"><img class="thumb" src="/graphs/'+esc(j.folder)+'/thumbnail.png"></a>':'';
return '<tr><td>'+esc(j.status)+'</td><td>'+esc(j.prompt)+'</td><td>'+esc(j.chart_type)+'</td><td>'+esc((j.indicators||[]).join(', '))+'</td><td>'+links+'</td><td>'+(j.folder?'<button onclick="replay(\\''+esc(j.folder)+'\\')">Replay</button>':'')+'</td></tr>'}).join('')+'</table>';
if(x.some(j=>['queued','planning','fetching','codegen','rendering','saving'].includes(j.status)))setTimeout(refresh,2000)}
async function run(){let r=await fetch('/api/graph',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:document.getElementById('prompt').value})});await r.json();refresh();setTimeout(refresh,2000)}
async function replay(f){await fetch('/api/replay/'+encodeURIComponent(f),{method:'POST'})}
refresh()
</script></main></body></html>"""


def create_app(service=None):
    from .service import GraphService
    svc = service or GraphService()
    app = Flask(__name__)

    @app.get("/")
    def index():
        return PAGE

    @app.post("/api/graph")
    def graph():
        body = request.get_json(silent=True) or {}
        prompt = str(body.get("prompt", "")).strip()
        if not prompt:
            return jsonify({"error": "prompt is required"}), 400
        return jsonify(svc.submit(prompt))

    @app.get("/api/history")
    def history():
        return jsonify(svc.history_view())

    @app.post("/api/replay/<folder>")
    def replay(folder):
        target = (GRAPHS_DIR / folder).resolve()
        if not target.is_relative_to(GRAPHS_DIR.resolve()) or not target.is_dir():
            return jsonify({"error": "unknown folder"}), 404
        svc.launch(target)
        return jsonify({"launched": folder})

    @app.get("/graphs/<path:name>")
    def graphs(name):
        return send_from_directory(GRAPHS_DIR, name)

    return app
