"""Tests for live mission status files (missions/status/*.json) and GitSync."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import urllib.error

import pygame  # noqa: E402
import pytest  # noqa: E402

from kingdom.app import App  # noqa: E402
from kingdom.castle import CastleScene  # noqa: E402
from kingdom.data import load_snapshot, parse_queue_line, read_statuses  # noqa: E402
from kingdom.gitsync import GitSync  # noqa: E402

SESSION_URL = "https://app.devin.ai/sessions/01f0724401894160a101b8f13eeba08b"


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _status(mid, state, **kw):
    data = {
        "schema_version": 1,
        "mission_id": mid,
        "state": state,
        "title": kw.pop("title", f"Title {mid}"),
        "hypothesis": kw.pop("hypothesis", f"Hypothesis {mid}"),
        "stage": kw.pop("stage", "stats"),
        "progress": kw.pop("progress", 0.5),
        "signal": kw.pop("signal", None),
        "message": kw.pop("message", ""),
        "agent_session_url": kw.pop("agent_session_url", ""),
        "run_folder": kw.pop("run_folder", ""),
        "round": kw.pop("round", ""),
        "parent_mission_id": kw.pop("parent_mission_id", ""),
        "scores": kw.pop("scores", {}),
        "trade_idea": kw.pop("trade_idea", None),
    }
    data.update(kw)
    return data


def _write_status(root: Path, status: dict):
    status_dir = root / "missions" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / f"{status['mission_id']}.json").write_text(json.dumps(status))


def _make_root(tmp_path: Path) -> Path:
    missions = tmp_path / "missions"
    (missions / "runs").mkdir(parents=True)
    (missions / "status").mkdir()
    return tmp_path


def test_running_status_active(tmp_path):
    root = _make_root(tmp_path)
    now = time.time()
    started = datetime.fromtimestamp(now - 300, tz=timezone.utc)
    updated = datetime.fromtimestamp(now, tz=timezone.utc)
    _write_status(root, _status(
        "R2-0042", "running", title="Hormuz share leads Brent-WTI",
        hypothesis="GDELT Hormuz share leads the Brent-WTI spread.",
        stage="stats", progress=0.55, signal=0.3,
        message="Permutation test running.", agent_session_url=SESSION_URL,
        started_at=_ts(started), updated_at=_ts(updated), elapsed_s=300,
    ))
    snap = load_snapshot(root, now)
    assert len(snap.active) == 1
    m = snap.active[0]
    assert m.mission_id == "R2-0042"
    assert m.stage == "stats"
    assert m.progress == pytest.approx(0.55)
    assert m.signal() == pytest.approx(0.3)
    assert m.agent_tag == "01f07244"
    assert m.elapsed(now) == pytest.approx(300, abs=2)
    assert m.display_title == "Hormuz share leads Brent-WTI"
    assert m.message == "Permutation test running."
    assert snap.counts["live"] == 1


def test_queued_and_legacy_fallback(tmp_path):
    root = _make_root(tmp_path)
    _write_status(root, _status("R2-0007", "queued", hypothesis="Shared hypothesis."))
    (root / "missions" / "in_progress.txt").write_text(
        "Shared hypothesis.\nLegacy only mission.\n")
    snap = load_snapshot(root)
    hyps = [m.hypothesis for m in snap.active]
    assert hyps.count("Shared hypothesis.") == 1
    assert "Legacy only mission." in hyps
    assert snap.active[0].state == "queued"
    assert snap.active[0].mission_id == "R2-0007"


def test_done_status_merges_with_run(tmp_path):
    root = _make_root(tmp_path)
    run = root / "missions" / "runs" / "20260921-131-gdelt_x_finance"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({
        "mission_id": "R2-0009", "hypothesis": "x leads y", "status": "ok",
        "n_obs": 88, "r": 0.21, "perm_p": 0.03}))
    trade = {"instrument": "BZ=F", "direction": "long", "holding_days": 3,
             "hit_rate": 0.61, "avg_return": 0.012, "n_trades": 28}
    _write_status(root, _status(
        "R2-0009", "done", run_folder="missions/runs/20260921-131-gdelt_x_finance",
        scores={"validity": 7.0, "interestingness": 5.0, "unexpectedness": 4.0, "actionability": 6.5},
        trade_idea=trade, agent_session_url=SESSION_URL, round="iran-round-2",
        finished_at="2026-09-21T04:00:00Z"))
    snap = load_snapshot(root)
    assert len(snap.completed) == 1
    m = snap.completed[0]
    assert m.actionability == pytest.approx(6.5)
    assert m.trade_idea == trade
    assert m.r == pytest.approx(0.21)
    assert m.n_obs == 88
    assert m.agent_tag == "01f07244"
    assert m.round == "iran-round-2"
    assert m.status == "ok"


def test_done_status_without_run_synthesizes(tmp_path):
    root = _make_root(tmp_path)
    _write_status(root, _status(
        "R2-0050", "done", hypothesis="Synth mission.", scores={"validity": 5.0},
        finished_at="2026-09-21T05:00:00Z"))
    _write_status(root, _status("R2-0051", "failed", hypothesis="Broke.", message="boom"))
    snap = load_snapshot(root)
    by_id = {m.mission_id: m for m in snap.completed}
    ok = by_id["R2-0050"]
    bad = by_id["R2-0051"]
    assert ok.status == "ok" and not ok.failed and ok.hypothesis == "Synth mission."
    assert ok.validity == pytest.approx(5.0)
    assert bad.failed and bad.status == "failed"
    # folder == mission_id sorts first
    assert snap.completed[0].mission_id in {"R2-0050", "R2-0051"}
    assert snap.completed[0].folder == snap.completed[0].mission_id


def test_malformed_statuses_ignored(tmp_path):
    root = _make_root(tmp_path)
    status_dir = root / "missions" / "status"
    (status_dir / "bad.json").write_text("{not json")
    (status_dir / "no_id.json").write_text(json.dumps({"state": "running"}))
    (status_dir / "SCHEMA.md").write_text("# schema")
    (status_dir / "archive").mkdir()
    (status_dir / "archive" / "old.json").write_text(json.dumps({"mission_id": "R0-1", "state": "done"}))
    statuses = read_statuses(status_dir)
    assert statuses == []
    snap = load_snapshot(root)
    assert snap.active == [] and snap.completed == []


def test_parse_queue_line():
    item = parse_queue_line("R2 | R2-0017 | Hormuz share leads spread")
    assert item.round == "R2"
    assert item.parent_mission_id == "R2-0017"
    assert item.text == "Hormuz share leads spread"
    plain = parse_queue_line("Just a hypothesis with | pipes")
    assert plain.round == "" and plain.parent_mission_id == ""
    assert plain.text == "Just a hypothesis with | pipes"
    mid = parse_queue_line("R2 | M20260920-a1ce90 | followup")
    assert mid.parent_mission_id == "M20260920-a1ce90"


def test_gitsync(tmp_path):
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    sync = GitSync(tmp_path, interval=0.01, runner=fake_run)
    (tmp_path / ".git").mkdir()
    sync.enabled = True
    sync.start()
    deadline = time.time() + 5
    while sync.status == "syncing" and time.time() < deadline:
        time.sleep(0.01)
    assert calls and calls[0][0] == ["git", "pull", "--rebase", "--autostash", "--quiet"]
    assert calls[0][1]["cwd"] == tmp_path
    assert sync.status == "ok"
    assert sync.tick(time.time()) is True
    sync._finished = False
    assert sync.tick(time.time()) is False
    sync.stop()

    def bad_run(cmd, **kw):
        raise RuntimeError("no git")

    err = GitSync(tmp_path, interval=0.01, runner=bad_run)
    err.start()
    deadline = time.time() + 5
    while err.status == "syncing" and time.time() < deadline:
        time.sleep(0.01)
    assert err.status == "error"
    assert "no git" in err.last_error
    err.stop()

    off = GitSync(tmp_path / "nonexistent", runner=fake_run)
    off.start()
    assert off.status == "off"
    n_calls = len(calls)
    assert off.tick(time.time()) is False
    assert len(calls) == n_calls


def _live_root(tmp_path: Path) -> Path:
    root = _make_root(tmp_path)
    _write_status(root, _status("R2-0001", "running", title="Live one", stage="judging",
                                progress=0.7, signal=0.8, message="Judging now.",
                                agent_session_url=SESSION_URL))
    _write_status(root, _status("R2-0002", "queued", title="Queued one"))
    (root / "missions" / "queue.txt").write_text(
        "R2 | R2-0017 | Hormuz share leads spread\nPlain hypothesis\n")
    run = root / "missions" / "runs" / "20260921-140-live-done"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({
        "mission_id": "R2-0003", "hypothesis": "done hyp", "status": "ok", "r": 0.1}))
    _write_status(root, _status(
        "R2-0003", "done", run_folder="missions/runs/20260921-140-live-done",
        scores={"validity": 6.0, "actionability": 7.0},
        trade_idea={"instrument": "BZ=F", "direction": "long", "holding_days": 3,
                    "hit_rate": 0.6, "avg_return": 0.01, "n_trades": 20},
        agent_session_url=SESSION_URL))
    return root


@pytest.mark.parametrize("menu", ["current", "queue", "completed"])
def test_live_menus_render(tmp_path, menu):
    root = _live_root(tmp_path)
    app = App(root=root, headless=True, poll_interval=0.0, pull_interval=None, http_interval=None)
    scene = CastleScene(app, menu=menu)
    app.push(scene, fade=False)
    for _ in range(5):
        app.step(1 / 30)
        canvas = app.render()
    colors = {canvas.get_at((x, y))[:3] for x in range(0, 480, 40) for y in range(0, 270, 30)}
    assert len(colors) > 1


def test_live_detail_renders(tmp_path):
    root = _live_root(tmp_path)
    app = App(root=root, headless=True, poll_interval=0.0, pull_interval=None, http_interval=None)
    scene = CastleScene(app, menu="completed")
    app.push(scene, fade=False)
    for _ in range(3):
        app.step(1 / 30)
        app.render()
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
    for _ in range(8):
        app.step(1 / 30)
        app.render()
    assert scene.detail is not None
    assert scene.detail.trade_idea


# -- HttpSync ------------------------------------------------------------------

class _FakeResp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_opener(responses):
    calls = []

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        calls.append(url)
        result = responses.get(url)
        if isinstance(result, Exception):
            raise result
        if result is None:
            raise urllib.error.HTTPError(url, 404, "nope", {}, None)
        return _FakeResp(result)

    return opener, calls


def test_httpsync_fetches_and_caches(tmp_path):
    import urllib.error  # noqa: F401
    from kingdom.httpsync import RAW_URL, STATUS_API, HttpSync

    repo = "o/r"
    api = STATUS_API.format(repo=repo, branch="main")
    raw_q = RAW_URL.format(repo=repo, branch="main", name="queue.txt")
    raw_ip = RAW_URL.format(repo=repo, branch="main", name="in_progress.txt")
    raw_f = RAW_URL.format(repo=repo, branch="main", name="failed.txt")
    dl1 = "https://raw/x/R2-0001.json"
    dl2 = "https://raw/x/R2-0002.json"
    responses = {
        api: json.dumps([
            {"type": "file", "name": "R2-0001.json", "download_url": dl1},
            {"type": "file", "name": "R2-0002.json", "download_url": dl2},
            {"type": "file", "name": "SCHEMA.md", "download_url": "https://raw/x/SCHEMA.md"},
        ]).encode(),
        dl1: json.dumps({"mission_id": "R2-0001", "state": "running"}).encode(),
        dl2: json.dumps({"mission_id": "R2-0002", "state": "queued"}).encode(),
        raw_q: b"queued hypothesis\n",
        raw_ip: b"live hypothesis\n",
        raw_f: urllib.error.HTTPError(raw_f, 404, "missing", {}, None),
    }
    cache = tmp_path / ".kingdom_cache" / "missions"
    cache.mkdir(parents=True)
    stale = cache / "status"
    stale.mkdir()
    (stale / "R2-9999.json").write_text("{}")
    (cache / "failed.txt").write_text("old")

    opener, calls = _fake_opener(responses)
    sync = HttpSync(tmp_path, repo=repo, enabled=True, opener=opener, cache_dir=cache)
    sync.start()
    deadline = time.time() + 5
    while sync.status == "syncing" and time.time() < deadline:
        time.sleep(0.01)
    assert sync.status == "ok"
    assert sync.tick(time.time()) is True
    sync._finished = False
    assert sync.tick(time.time()) is False
    sync.stop()
    assert (stale / "R2-0001.json").is_file()
    assert (stale / "R2-0002.json").is_file()
    assert not (stale / "R2-9999.json").exists()
    assert (cache / "queue.txt").read_text() == "queued hypothesis\n"
    assert not (cache / "failed.txt").exists()
    assert calls[0] == api


def test_httpsync_error_and_disabled(tmp_path):
    import urllib.error

    from kingdom.httpsync import HttpSync

    def boom(req, timeout=None):
        raise urllib.error.URLError("offline")

    sync = HttpSync(tmp_path, repo="o/r", enabled=True, opener=boom)
    sync.start()
    deadline = time.time() + 5
    while sync.status == "syncing" and time.time() < deadline:
        time.sleep(0.01)
    assert sync.status == "error"
    assert sync.last_error
    sync.stop()

    calls = []

    def track(req, timeout=None):
        calls.append(1)
        return _FakeResp(b"[]")

    off = HttpSync(tmp_path, repo="o/r", enabled=False, opener=track)
    off.start()
    assert off.status == "off"
    assert off.tick(time.time()) is False
    assert not calls


def test_overlay_precedence(tmp_path):
    root = _make_root(tmp_path)
    base = datetime(2026, 9, 21, 4, 0, 0, tzinfo=timezone.utc)
    _write_status(root, _status("R2-0001", "running", stage="stats",
                               updated_at=_ts(base)))
    (root / "missions" / "queue.txt").write_text("local queue line\n")
    overlay = tmp_path / "overlay"
    (overlay / "status").mkdir(parents=True)
    over = _status("R2-0001", "running", stage="judging", updated_at=_ts(base + timedelta(seconds=60)))
    (overlay / "status" / "R2-0001.json").write_text(json.dumps(over))
    (overlay / "queue.txt").write_text("overlay queue line\n")
    snap = load_snapshot(root, overlay=overlay)
    assert snap.active[0].stage == "judging"
    assert snap.queue == ["overlay queue line"]
    snap_local = load_snapshot(root)
    assert snap_local.active[0].stage == "stats"
