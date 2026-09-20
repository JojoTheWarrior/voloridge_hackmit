from pathlib import Path

import pandas as pd

from warsignal.mission.model import MissionPlan, MissionResult
from warsignal.mission import publish
from warsignal.mission import runner


def _result(status="ok"):
    plan = MissionPlan("finance.BZ=F.log_return", "finance.^GSPC.log_return")
    return MissionResult(
        "MTEST-run",
        "2026-09-20T00:00:00+00:00",
        "Brent and stocks move together",
        plan,
        stats={
            "n_obs": 3,
            "correlation": {"pearson_r": 0.2},
            "lagged": {"best_lag": 1},
            "perm_p": 0.2,
        },
        scores={"validity": 4, "interestingness": 5, "unexpectedness": 3},
        narrative_md="**Verdict:** not supported",
        status=status,
        error="failed" if status == "failed" else None,
        n_obs=3,
    )


def test_run_folder_counter_slug_and_contents(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr(publish, "RUNS", runs)
    monkeypatch.setattr(publish, "LOCK", runs / ".lock")
    raw = pd.Series([1, 2, 3], index=pd.date_range("2026-01-01", periods=3))
    folder = publish.write_run_folder(_result(), raw, raw, raw, raw, judge={"scores": {}})
    assert folder.name.endswith("finance-bz-f-log-return_x_finance-gspc-log-return")
    assert folder.name.split("-")[1] == "001"
    for name in (
        "hypothesis.txt", "plan.json", "stats.json", "judge.json", "note.md",
        "manifest.json", "data/aligned.csv", "data/raw_a.csv", "data/raw_b.csv",
    ):
        assert (folder / name).exists()
    failed = publish.write_run_folder(_result("failed"), judge={})
    assert failed.name.split("-")[1] == "002"
    assert "-FAILED-brent-and-stocks-move-together" in failed.name
    assert (runs / "INDEX.md").exists()


def test_publish_is_not_called_without_flag(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(publish, "publish_run", lambda folder: called.append(folder))
    assert called == []


def test_no_ai_mission_writes_self_contained_run(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "missions").mkdir(parents=True)
    runs = root / "missions" / "runs"
    monkeypatch.setattr(runner, "ROOT", root)
    monkeypatch.setattr(publish, "RUNS", runs)
    monkeypatch.setattr(publish, "LOCK", runs / ".lock")
    plan = MissionPlan("finance.BZ=F.close", "finance.^GSPC.close")
    index = pd.date_range("2025-03-01", periods=30, freq="D")
    monkeypatch.setattr(runner, "plan_mission", lambda hypothesis, use_ai=True: (plan, "heuristic"))
    monkeypatch.setattr(runner, "get_series", lambda name, start, end: pd.Series(range(30), index=index))
    result = runner.run_mission("cached no-ai mission", use_ai=False)
    folder = Path(result.artifacts["run_folder"])
    assert folder.parent == runs
    assert (folder / "data" / "aligned.csv").exists()
    assert (folder / "judge.json").exists()
    assert result.artifacts["report_path"].endswith("/note.md")
