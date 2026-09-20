"""Tests for kingdom.data — the read-only missions/ adapter."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from kingdom.data import (
    ActiveMission,
    CompletedMission,
    DataAdapter,
    Snapshot,
    load_snapshot,
    read_index,
    read_run,
    signal_strength,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _missions(tmp_path: Path) -> Path:
    m = tmp_path / "missions"
    (m / "runs").mkdir(parents=True)
    return m


def _run_dir(missions: Path, name: str) -> Path:
    d = missions / "runs" / name
    d.mkdir(parents=True)
    return d


def test_empty_root(tmp_path):
    snap = load_snapshot(tmp_path)
    assert snap.queue == [] and snap.active == [] and snap.completed == [] and snap.failed == []
    assert snap.counts == {"active": 0, "queued": 0, "completed_ok": 0, "failed": 0, "live": 0}


def test_queue_blank_lines(tmp_path):
    m = _missions(tmp_path)
    (m / "queue.txt").write_text("hyp one\n\n   \nhyp two\n")
    snap = load_snapshot(tmp_path)
    assert snap.queue == ["hyp one", "hyp two"]


def test_active_mtime_fallback(tmp_path):
    m = _missions(tmp_path)
    p = m / "in_progress.txt"
    p.write_text("hyp A\nhyp B\n")
    os.utime(p, (1000.0, 1000.0))
    snap = load_snapshot(tmp_path, now=1010.0)
    assert len(snap.active) == 2
    assert all(a.started_at == 1000.0 for a in snap.active)
    assert snap.active[0].elapsed(1010.0) == 10.0


def test_active_timestamp_prefix(tmp_path):
    m = _missions(tmp_path)
    p = m / "in_progress.txt"
    p.write_text("2026-09-20T10:00:00Z\thyp with ts\nplain hyp\n")
    os.utime(p, (500.0, 500.0))
    snap = load_snapshot(tmp_path, now=600.0)
    assert snap.active[0].hypothesis == "hyp with ts"
    assert snap.active[0].started_at == pytest.approx(1789898400.0)
    assert snap.active[1].started_at == 500.0


def test_ok_run_all_files(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260920-001-my-mission")
    (d / "hypothesis.txt").write_text("Iran news leads Brent\n")
    (d / "manifest.json").write_text(json.dumps({
        "hypothesis": "Iran news leads Brent",
        "status": "ok",
        "n_obs": 42,
        "r": 0.31,
        "perm_p": 0.02,
        "validity": 7.5,
        "interestingness": 6.0,
        "unexpectedness": 5.5,
        "created_at": "2026-09-20T12:00:00Z",
        "mission_id": "M20260920-abc",
    }))
    (d / "stats.json").write_text(json.dumps({"n_obs": 42, "correlation": {"pearson_r": 0.31}, "perm_p": 0.02}))
    (d / "judge.json").write_text(json.dumps({"scores": {"validity": 7.5, "interestingness": 6.0, "unexpectedness": 5.5}}))
    (d / "note.md").write_text("# report")
    (d / "viz.png").write_bytes(b"")
    snap = load_snapshot(tmp_path)
    assert len(snap.completed) == 1
    c = snap.completed[0]
    assert c.status == "ok" and not c.failed
    assert c.hypothesis == "Iran news leads Brent"
    assert c.n_obs == 42 and c.r == 0.31 and c.perm_p == 0.02
    assert c.validity == 7.5 and c.interestingness == 6.0 and c.unexpectedness == 5.5
    assert c.mission_id == "M20260920-abc"
    assert c.created_at == pytest.approx(1789905600.0)
    assert c.viz_path is not None and c.note_path is not None
    assert c.note_text() == "# report"


def test_failed_run_only_hypothesis(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260919-002-FAILED-broken-mission")
    (d / "hypothesis.txt").write_text("oil vs news\n")
    snap = load_snapshot(tmp_path)
    c = snap.completed[0]
    assert c.status == "failed" and c.failed
    assert c.hypothesis == "oil vs news"


def test_malformed_manifest_falls_back(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260918-003-garbage-manifest")
    (d / "manifest.json").write_bytes(b"\xff\xfe{not json")
    (d / "hypothesis.txt").write_text("fallback hyp\n")
    (d / "stats.json").write_text(json.dumps({"n_obs": 11, "correlation": {"pearson_r": -0.2}, "perm_p": 0.4}))
    (d / "judge.json").write_text(json.dumps({"scores": {"validity": 3.0}}))
    c = read_run(d)
    assert c is not None
    assert c.hypothesis == "fallback hyp"
    assert c.status == "unknown"
    assert c.n_obs == 11 and c.r == -0.2 and c.perm_p == 0.4 and c.validity == 3.0


def test_index_row_only(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260917-004-index-only")
    index = read_index(_write_index(m, [
        "| `20260917-004-index-only` | index hyp | ok | 25 | 0.5 | 0.01 | 8 | 7 | 6 |",
    ]))
    c = read_run(d, index=index)
    assert c.status == "ok"
    assert c.hypothesis == "index hyp"
    assert c.n_obs == 25 and c.r == 0.5 and c.perm_p == 0.01
    assert c.validity == 8 and c.interestingness == 7 and c.unexpectedness == 6


def _write_index(missions: Path, rows: list[str]) -> Path:
    p = missions / "runs" / "INDEX.md"
    header = "# Runs\n\n| folder | hypothesis | status | n | r | perm_p | Validity | Interest | Unexpected |\n|---|---|---|---|---|---|---|---|---|\n"
    p.write_text(header + "\n".join(rows) + "\n")
    return p


def test_nullish_values_in_manifest_and_index(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260916-005-nulls")
    (d / "manifest.json").write_text(json.dumps({
        "hypothesis": "nulls",
        "status": "ok",
        "n_obs": None,
        "r": "nan",
        "perm_p": "None",
        "validity": float("nan") if False else "null",
    }))
    index = read_index(_write_index(m, [
        "| `20260916-005-nulls` | nulls | ok | None | nan | None | None |  | None |",
    ]))
    c = read_run(d, index=index)
    assert c.n_obs is None and c.r is None and c.perm_p is None
    assert c.validity is None and c.interestingness is None and c.unexpectedness is None


def test_manifest_null_falls_back_to_index(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260915-006-manifest-null-index-fill")
    (d / "manifest.json").write_text(json.dumps({"hypothesis": "h", "status": "ok", "r": None, "validity": None}))
    index = read_index(_write_index(m, [
        "| `20260915-006-manifest-null-index-fill` | h | ok | 10 | 0.9 | 0.5 | 4 | None | None |",
    ]))
    c = read_run(d, index=index)
    assert c.r == 0.9 and c.validity == 4


def test_completed_sorted_newest_first(tmp_path):
    m = _missions(tmp_path)
    for name in ["20260910-001-old", "20260920-001-new", "20260915-001-mid"]:
        d = _run_dir(m, name)
        (d / "manifest.json").write_text(json.dumps({"status": "ok", "hypothesis": name}))
    snap = load_snapshot(tmp_path)
    assert [c.folder for c in snap.completed] == [
        "20260920-001-new", "20260915-001-mid", "20260910-001-old",
    ]


def test_signal_strength_edges():
    assert signal_strength(0.0, None) == 0.0
    assert signal_strength(10.0, None) == 1.0
    assert signal_strength(None, None) is None
    assert signal_strength(None, 0.0) == 1.0
    assert signal_strength(None, 1.0) == 0.0
    # validity wins over perm_p
    assert signal_strength(5.0, 0.9) == 0.5
    assert ActiveMission(hypothesis="h", started_at=0).signal() is None


def test_adapter_poll_caching(tmp_path, monkeypatch):
    _missions(tmp_path)
    adapter = DataAdapter(tmp_path, poll_interval=2)
    snap0 = adapter.snapshot(now=0.0)
    assert adapter.snapshot(now=1.0) is snap0

    calls = []
    import kingdom.data as kd
    real = kd.load_snapshot
    monkeypatch.setattr(kd, "load_snapshot", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    adapter.snapshot(now=1.5)
    assert calls == []
    adapter.snapshot(now=3.0)
    assert calls == [1]


def test_run_cache_invalidation(tmp_path):
    m = _missions(tmp_path)
    d = _run_dir(m, "20260920-001-cached")
    manifest = d / "manifest.json"
    manifest.write_text(json.dumps({"status": "ok", "hypothesis": "h", "validity": 2.0}))
    adapter = DataAdapter(tmp_path, poll_interval=0)
    c1 = adapter.snapshot(now=0).completed[0]
    assert c1.validity == 2.0
    # unchanged -> same object identity
    c2 = adapter.snapshot(now=1).completed[0]
    assert c2 is c1
    # bump manifest + dir mtime -> re-read
    manifest.write_text(json.dumps({"status": "ok", "hypothesis": "h", "validity": 9.0}))
    t = d.stat().st_mtime + 10
    os.utime(manifest, (t, t))
    os.utime(d, (t, t))
    c3 = adapter.snapshot(now=2).completed[0]
    assert c3 is not c1 and c3.validity == 9.0


def test_refresh_never_raises(tmp_path, monkeypatch):
    adapter = DataAdapter(tmp_path)
    import kingdom.data as kd
    monkeypatch.setattr(kd, "load_snapshot", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    snap = adapter.snapshot(now=5.0)
    assert isinstance(snap, Snapshot)
    # second failure returns previous snapshot content, doesn't raise
    snap2 = adapter.refresh(now=6.0)
    assert snap2.loaded_at == 6.0


def test_counts_and_age(tmp_path):
    m = _missions(tmp_path)
    ok = _run_dir(m, "20260920-001-ok")
    (ok / "manifest.json").write_text(json.dumps({
        "status": "ok", "hypothesis": "h", "created_at": "2026-09-20T00:00:00Z",
    }))
    bad = _run_dir(m, "20260919-001-FAILED-x")
    (bad / "hypothesis.txt").write_text("gone\n")
    (m / "queue.txt").write_text("q1\nq2\n")
    (m / "in_progress.txt").write_text("act\n")
    snap = load_snapshot(tmp_path, now=0)
    assert snap.counts == {"active": 1, "queued": 2, "completed_ok": 1, "failed": 1, "live": 0}
    c = snap.completed[0]
    assert c.age(c.created_at + 30) == 30.0
    assert CompletedMission(folder="f", path=tmp_path).age() is None


def test_real_repo_missions():
    snap = load_snapshot(REPO_ROOT)
    assert len(snap.completed) >= 1
    assert any(c.hypothesis.strip() for c in snap.completed)
    assert any(c.status == "failed" for c in snap.completed)
