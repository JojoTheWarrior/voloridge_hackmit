"""Tests for warsignal.mission.monitor and the terminal Flask app."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from terminal.app import create_app, index_html
from warsignal.mission.monitor import (
    Monitor,
    build_runs,
    diff_statuses,
    leaderboard,
    parse_queue_line,
    read_queue_entries,
    read_results_csv,
    read_status_dir,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

# tiny valid PNG (1x1)
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082"
)


def _missions(tmp_path: Path) -> Path:
    m = tmp_path / "missions"
    (m / "runs").mkdir(parents=True)
    (m / "status" / "archive").mkdir(parents=True)
    return m


def _status(mid: str, **over) -> dict:
    base = {
        "schema_version": 1,
        "mission_id": mid,
        "title": f"title {mid}",
        "hypothesis": f"hyp {mid}",
        "state": "running",
        "stage": "stats",
        "progress": None,
        "signal": 0.4,
        "started_at": "2026-09-21T03:10:00Z",
        "updated_at": "2026-09-21T03:16:30Z",
        "finished_at": None,
        "message": "working",
        "scores": {"validity": 7.0, "interestingness": 5.0,
                   "unexpectedness": 4.0, "actionability": 8.0},
        "trade_idea": None,
        "agent_session_url": "https://app.devin.ai/sessions/x",
        "brain_sessions": [{"purpose": "planner",
                            "session_url": "https://app.devin.ai/sessions/b"}],
    }
    base.update(over)
    return base


def _write_status(m: Path, mid: str, **over):
    (m / "status" / f"{mid}.json").write_text(json.dumps(_status(mid, **over)))


def _run_dir(m: Path, name: str) -> Path:
    d = m / "runs" / name
    d.mkdir(parents=True)
    return d


def _fixture_run(m: Path, name="20260921-001-a_x_b", mission_id="M1",
                 validity=8.5, bonferroni_p=0.04) -> Path:
    d = _run_dir(m, name)
    (d / "hypothesis.txt").write_text("A leads B")
    (d / "manifest.json").write_text(json.dumps({
        "mission_id": mission_id, "folder": name, "hypothesis": "A leads B",
        "status": "ok", "created_at": "2026-09-21T01:00:00+00:00",
        "n_obs": 120, "r": 0.25, "perm_p": 0.01, "validity": validity,
    }))
    (d / "stats.json").write_text(json.dumps({
        "n_obs": 120, "coverage_start": "2025-03-01", "coverage_end": "2026-09-15",
        "correlation": {"pearson_r": 0.25, "spearman_r": 0.2},
        "lagged": {"lags": [-2, -1, 0, 1, 2], "r": [0.05, 0.1, 0.25, -0.4, 0.02],
                   "best_lag": 0, "best_r": 0.25},
        "perm_p": 0.01, "n_lags_tested": 5, "bonferroni_p": bonferroni_p,
        "pre_post": {"effect_size": 0.7}, "window": "full",
    }))
    (d / "judge.json").write_text(json.dumps({
        "scores": {"validity": validity, "interestingness": 6.0,
                   "unexpectedness": 5.5, "actionability": 7.5,
                   "supported_prob": 0.8, "judge_model": "jev-1"},
        "judge": "jev", "model": "jev-1",
    }))
    (d / "note.md").write_text("# Note\n\nsome **bold** text\n")
    (d / "viz.png").write_bytes(PNG)
    return d


# ---------- parse_queue_line ----------

def test_parse_queue_line_plain():
    assert parse_queue_line("just a hypothesis") == {
        "round": "", "parent_id": "", "hypothesis": "just a hypothesis"}


def test_parse_queue_line_round():
    assert parse_queue_line("[iran-round-2] oil leads news")["round"] == "iran-round-2"


def test_parse_queue_line_round_parent():
    e = parse_queue_line("[r3 <- R2-0017] followup hyp")
    assert e["round"] == "r3" and e["parent_id"] == "R2-0017"
    assert e["hypothesis"] == "followup hyp"


def test_parse_queue_line_tabs():
    e = parse_queue_line("r2\tR2-0001\ttabbed hyp")
    assert e["round"] == "r2" and e["parent_id"] == "R2-0001"
    assert e["hypothesis"] == "tabbed hyp"


def test_read_queue_entries_positions(tmp_path):
    m = _missions(tmp_path)
    (m / "queue.txt").write_text("[r1] a\nplain b\n")
    entries = read_queue_entries(m / "queue.txt")
    assert [e["position"] for e in entries] == [1, 2]
    assert entries[0]["round"] == "r1" and entries[1]["hypothesis"] == "plain b"


# ---------- read_status_dir ----------

def test_read_status_dir(tmp_path):
    m = _missions(tmp_path)
    now = 1789963800.0  # after the fixture's started_at (2026-09-21T03:10Z)
    _write_status(m, "R1", state="running", stage="stats")
    _write_status(m, "R2", state="done", stage="done", progress=1.0,
                  finished_at="2026-09-21T03:20:00Z", elapsed_s=None)
    _write_status(m, "R3", state="queued", stage="queued", started_at=None)
    entries = {e["mission_id"]: e for e in read_status_dir(m / "status", now)}
    running = entries["R1"]
    assert running["state"] == "running"
    assert running["progress"] == pytest.approx(0.3)  # stats index 3 / 10
    assert running["elapsed_s"] > 0
    assert running["scores"]["actionability"] == 8.0
    done = entries["R2"]
    assert done["elapsed_s"] == 600  # finished - started
    assert entries["R3"]["state"] == "queued"


def test_read_status_dir_malformed_and_archive(tmp_path):
    m = _missions(tmp_path)
    (m / "status" / "bad.json").write_text("{not json")
    (m / "status" / "archive" / "old.json").write_text(
        json.dumps(_status("OLD")))
    _write_status(m, "GOOD")
    entries = read_status_dir(m / "status", time.time())
    ids = [e["mission_id"] for e in entries]
    assert "GOOD" in ids and "OLD" not in ids


def test_running_elapsed_recomputed(tmp_path):
    """Running statuses recompute elapsed from started_at, ignoring stored elapsed_s."""
    m = _missions(tmp_path)
    started = (datetime.now(timezone.utc) - timedelta(seconds=600)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_status(m, "R", state="running", started_at=started, elapsed_s=5)
    entry = read_status_dir(m / "status", time.time())[0]
    assert entry["elapsed_s"] == pytest.approx(600, abs=2)


def test_done_keeps_stored_elapsed(tmp_path):
    m = _missions(tmp_path)
    _write_status(m, "D", state="done", elapsed_s=5,
                  finished_at="2026-09-21T03:20:00Z")
    entry = read_status_dir(m / "status", time.time())[0]
    assert entry["elapsed_s"] == 5


def test_status_malformed_skipped(tmp_path):
    m = _missions(tmp_path)
    (m / "status" / "broken.json").write_text("{")
    (m / "status" / "array.json").write_text("[]")
    _write_status(m, "OK")
    entries = read_status_dir(m / "status", time.time())
    assert [e["mission_id"] for e in entries] == ["OK"]


def test_read_status_dir_ordering(tmp_path):
    m = _missions(tmp_path)
    _write_status(m, "Q", state="queued")
    _write_status(m, "R", state="running")
    _write_status(m, "D", state="done")
    entries = read_status_dir(m / "status", time.time())
    states = [e["state"] for e in entries]
    assert states.index("running") < states.index("queued") < states.index("done")


# ---------- results.csv / build_runs ----------

def test_read_results_csv(tmp_path):
    p = tmp_path / "results.csv"
    p.write_text("mission_id,folder,validity,actionability\nM1,f1,7,9\n")
    rows = read_results_csv(p)
    assert rows["M1"]["actionability"] == "9"
    assert read_results_csv(tmp_path / "missing.csv") == {}


def test_build_runs(tmp_path):
    m = _missions(tmp_path)
    _fixture_run(m)
    runs = build_runs(tmp_path, {}, [], cache={})
    assert len(runs) == 1
    r = runs[0]
    assert r["folder"] == "20260921-001-a_x_b"
    assert r["mission_id"] == "M1" and r["status"] == "ok"
    assert r["n"] == 120 and r["r"] == pytest.approx(0.25)
    assert r["best_lag"] == 1  # max |r| is lag=1 at -0.4
    assert r["bonferroni_ok"] is True
    assert r["actionability"] == pytest.approx(7.5)  # judge scores win
    assert r["validity"] == pytest.approx(8.5)
    assert r["has_viz"] and r["has_note"]
    json.dumps(runs)  # JSON-safe


def test_build_runs_actionability_fallback(tmp_path):
    m = _missions(tmp_path)
    d = _fixture_run(m)
    judge = json.loads((d / "judge.json").read_text())
    del judge["scores"]["actionability"]
    (d / "judge.json").write_text(json.dumps(judge))
    results = {"M1": {"mission_id": "M1", "actionability": "3.5"}}
    runs = build_runs(tmp_path, results, [], cache={})
    assert runs[0]["actionability"] == pytest.approx(3.5)


def test_build_runs_extra_cache_invalidation(tmp_path):
    """Editing judge.json (not manifest) must invalidate the extra cache."""
    import os

    m = _missions(tmp_path)
    d = _fixture_run(m)
    cache = {}
    assert build_runs(tmp_path, {}, [], cache=cache)[0]["actionability"] == 7.5
    judge = json.loads((d / "judge.json").read_text())
    judge["scores"]["actionability"] = 1.0
    (d / "judge.json").write_text(json.dumps(judge))
    future = time.time() + 10
    os.utime(d / "judge.json", (future, future))
    assert build_runs(tmp_path, {}, [], cache=cache)[0]["actionability"] == 1.0


def test_build_runs_trade_idea_from_status(tmp_path):
    m = _missions(tmp_path)
    _fixture_run(m)
    st = _status("M1", state="done", run_folder="missions/runs/20260921-001-a_x_b",
                 trade_idea={"instrument": "BZ=F", "direction": "long"})
    runs = build_runs(tmp_path, {}, [st], cache={})
    assert runs[0]["trade_idea"]["instrument"] == "BZ=F"
    assert runs[0]["agent_session_url"].endswith("/x")


# ---------- leaderboard ----------

def test_leaderboard_ordering(tmp_path):
    runs = [
        {"status": "ok", "validity": 5.0, "perm_p": 0.01, "folder": "a",
         "mission_id": "a", "effect": 0.1, "n": 10},
        {"status": "ok", "validity": 9.0, "perm_p": 0.5, "folder": "b",
         "mission_id": "b", "effect": 0.2, "n": 10},
        {"status": "ok", "validity": 9.0, "perm_p": 0.01, "folder": "c",
         "mission_id": "c", "effect": 0.3, "n": 10},
        {"status": "failed", "validity": 9.9, "perm_p": 0.0, "folder": "d",
         "mission_id": "d"},
        {"status": "ok", "validity": None, "perm_p": 0.0, "folder": "e",
         "mission_id": "e"},
    ]
    lb = leaderboard(runs)
    assert [r["mission_id"] for r in lb] == ["c", "b", "a"]
    assert lb[0]["rank"] == 1


# ---------- diff_statuses ----------

def test_diff_statuses():
    old = [_status("A", state="running", stage="stats"),
           _status("B", state="running")]
    new = [_status("A", state="running", stage="viz", message="rendering"),
           _status("C", state="queued")]
    events = diff_statuses(old, new, "2026-09-21T00:00:00Z")
    by_id = {}
    for e in events:
        by_id.setdefault(e["mission_id"], []).append(e)
    assert by_id["C"][0]["kind"] == "new"
    assert by_id["B"][0]["kind"] == "gone"
    assert any(e["field"] == "stage" and e["new"] == "viz" for e in by_id["A"])
    assert all(e["at"] == "2026-09-21T00:00:00Z" for e in events)


# ---------- Monitor ----------

def test_monitor_state_json(tmp_path):
    m = _missions(tmp_path)
    _fixture_run(m)
    _write_status(m, "R1", state="running")
    (m / "queue.txt").write_text("queued hyp\n")
    (m / "failed.txt").write_text("bad hyp\tsome error\n")
    (m / "config.json").write_text('{"max_agents": 5}')
    mon = Monitor(tmp_path, pull=False)
    state = mon.state()
    json.dumps(state)  # must be JSON-serialisable
    assert state["counts"]["running"] == 1
    assert state["counts"]["done"] == 1
    assert state["counts"]["failed"] == 1
    assert len(state["queue"]) == 1
    assert len(state["runs"]) == 1
    for key in ("generated_at", "git", "config", "counts", "active",
                "statuses", "queue", "runs", "leaderboard", "failed", "log"):
        assert key in state


def test_state_nonblocking_during_pull(tmp_path, monkeypatch):
    """``state()`` must return while a git pull is still in flight."""
    import warsignal.mission.monitor as mon_mod

    _missions(tmp_path)
    monkeypatch.setattr(mon_mod, "git_pull",
                        lambda root, timeout=30: (time.sleep(0.5), {"ok": True, "output": "", "at": "x"})[1])
    mon = Monitor(tmp_path, pull_interval=0, pull=True)
    mon.refresh()  # first build: state exists
    mon._last_pull_at = 0.0  # make the next refresh pull again
    worker = threading.Thread(target=mon.refresh)
    worker.start()
    time.sleep(0.05)  # pull is now sleeping inside refresh
    t0 = time.time()
    mon.state()
    assert time.time() - t0 < 0.2
    worker.join()


def test_state_returns_during_first_pull(tmp_path, monkeypatch):
    """state() on a fresh monitor must not deadlock while a pull runs."""
    import warsignal.mission.monitor as mon_mod

    _missions(tmp_path)
    monkeypatch.setattr(
        mon_mod, "git_pull",
        lambda root, timeout=30: (time.sleep(1), {"ok": True, "output": "", "at": "x"})[1])
    mon = Monitor(tmp_path, pull_interval=0, pull=True)
    worker = threading.Thread(target=mon.refresh)
    worker.start()
    time.sleep(0.05)  # pull in progress inside refresh
    mon.state()  # must return, not hang
    worker.join(timeout=5)
    assert not worker.is_alive()


# ---------- Flask app ----------

def _app(tmp_path):
    m = _missions(tmp_path)
    _fixture_run(m)
    return create_app(Monitor(tmp_path, pull=False)).test_client(), m


def test_api_state(tmp_path):
    client, _ = _app(tmp_path)
    r = client.get("/api/state")
    assert r.status_code == 200
    body = r.get_json()
    assert {"counts", "runs", "queue", "statuses"} <= set(body)


def test_api_run_and_traversal(tmp_path):
    client, _ = _app(tmp_path)
    r = client.get("/api/run/20260921-001-a_x_b")
    assert r.status_code == 200
    assert "some **bold**" in r.get_json()["note_md"]
    assert client.get("/api/run/..%2F..%2Fetc").status_code in (400, 404)
    assert client.get("/api/run/not-a-run").status_code == 404


def test_run_files(tmp_path):
    client, _ = _app(tmp_path)
    assert client.get("/runs/20260921-001-a_x_b/viz.png").status_code == 200
    assert client.get("/runs/20260921-001-a_x_b/missing.png").status_code == 404


def test_index_and_snapshot_routes(tmp_path):
    client, _ = _app(tmp_path)
    assert "WARSIGNAL TERMINAL" in client.get("/").get_data(as_text=True)
    snap = client.get("/snapshot").get_data(as_text=True)
    assert "window.__STATE__" in snap and "20260921-001-a_x_b" in snap
    # snapshot is self-contained: CSS/JS inlined, no /static/ references
    assert "/static/" not in snap
    assert "<style>" in snap


def test_index_html_embeds_state(tmp_path):
    html = index_html({"runs": [{"folder": "x"}], "counts": {}})
    assert "window.__STATE__ = {" in html
    assert "/static/" not in html and "<style>" in html


def test_write_snapshot(tmp_path):
    from terminal.snapshot import write_snapshot
    _missions(tmp_path)
    _fixture_run(tmp_path / "missions")
    out = write_snapshot(Monitor(tmp_path, pull=False), tmp_path / "snap.html")
    html = out.read_text()
    assert "window.__STATE__" in html
    assert "/static/" not in html and "<style>" in html
    assert "20260921-001-a_x_b" in html
    assert '"run_details"' in html
    assert '"20260921-001-a_x_b":' in html


# ---------- real repo ----------

def test_real_root_fast():
    mon = Monitor(REPO_ROOT, pull=False)
    t0 = time.time()
    state = mon.state()
    assert time.time() - t0 < 3.0
    assert len(state["runs"]) >= 100
    json.dumps(state)
