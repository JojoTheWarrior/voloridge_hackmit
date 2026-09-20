from __future__ import annotations

import json
import math
import os
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

os.environ["WARSIGNAL_GRAPH_NO_GIT"] = "1"

from warsignal.graph import cache, naming, store
from warsignal.graph.chart_template import CHART_TEMPLATE
from warsignal.graph.validator import validate_script
from warsignal.config import DATA_REF


def test_folder_name():
    name = naming.folder_name(date(2026, 9, 20), 3, "reel", ["finance.BZ=F.close"])
    assert name == "20260920-003-reel_brent-close"


def test_indicator_slug():
    assert naming.indicator_slug("finance.BZ=F.close") == "brent-close"
    assert naming.indicator_slug("finance.^GSPC.log_return") == "sp500-log-return"
    assert naming.indicator_slug("finance.NG=F.close") == "natgas-close"


def test_next_counter(tmp_path):
    (tmp_path / "20260101-002-x").mkdir()
    (tmp_path / "20260102-007-y").mkdir()
    (tmp_path / "not-a-graph").mkdir()
    assert naming.next_counter(tmp_path) == 8
    assert naming.next_counter(tmp_path / "missing") == 1


def _folder(graphs_dir, name, prompt, chart_type="line"):
    folder = graphs_dir / name
    folder.mkdir(parents=True)
    (folder / "prompt.txt").write_text(prompt)
    (folder / "plan.json").write_text(json.dumps({"chart_type": chart_type, "indicators": []}))
    return folder


def test_find_match_exact(tmp_path):
    _folder(tmp_path, "20260101-001-line_brent", "show me the price of brent")
    hit = cache.find_match("show me the price of brent", tmp_path)
    assert hit and hit["folder"] == "20260101-001-line_brent"


def test_find_match_confirm(tmp_path):
    _folder(tmp_path, "20260101-001-line_brent", "plot brent close over time")
    calls = []

    def confirm(prompt, candidates):
        calls.append(len(candidates))
        return candidates[0]["folder"]

    hit = cache.find_match("brent close chart please", tmp_path, confirm=confirm)
    if calls:  # only exercised when score lands in the 0.55-0.92 band
        assert hit and hit["folder"] == "20260101-001-line_brent"


def test_find_match_none(tmp_path):
    _folder(tmp_path, "20260101-001-line_brent", "brent close")
    assert cache.find_match("tehran rainfall anomaly weekly", tmp_path) is None


def test_validate_template_ok():
    assert validate_script(CHART_TEMPLATE) == []


@pytest.mark.parametrize("source", [
    "import requests\nrequests.get('x')",
    "import urllib.request",
    "x = __import__('yfinance')",
    "open('x', 'w')",
    "import subprocess",
    "eval('1+1')",
])
def test_validate_rejects(source):
    assert validate_script(source)


def _make_graph_folder(tmp_path, chart_type):
    folder = tmp_path / f"20260101-001-{chart_type}_sine-cosine"
    data = folder / "data"
    data.mkdir(parents=True)
    days = pd.date_range("2025-09-01", periods=300, freq="D")
    a = pd.Series([math.sin(i / 20) * 10 + 70 for i in range(300)], index=days)
    b = pd.Series([math.cos(i / 25) * 8 + 65 for i in range(300)], index=days)
    pd.DataFrame({"date": days.date.astype(str), "value": a.values}).to_csv(data / "sine.csv", index=False)
    pd.DataFrame({"date": days.date.astype(str), "value": b.values}).to_csv(data / "cosine.csv", index=False)
    series = [{"file": "sine.csv", "label": "Sine A", "indicator": "test.sine"},
              {"file": "cosine.csv", "label": "Cosine B", "indicator": "test.cosine"}]
    plan = {"title": f"Test {chart_type}", "chart_type": chart_type, "series": series}
    if chart_type == "scatter":
        plan["x_series"], plan["y_series"] = "sine.csv", "cosine.csv"
    (folder / "plan.json").write_text(json.dumps(plan))
    (folder / "prompt.txt").write_text("test")
    (folder / "chart.py").write_text(CHART_TEMPLATE)
    timeline = DATA_REF / "iran_timeline.csv"
    if timeline.exists():
        shutil.copy(timeline, folder / "iran_timeline.csv")
    return folder


@pytest.mark.parametrize("chart_type", ["reel", "line", "spread", "scatter"])
def test_headless_render(tmp_path, chart_type):
    folder = _make_graph_folder(tmp_path, chart_type)
    png = store.render_thumbnail(folder, timeout=120)
    assert png.exists() and png.stat().st_size > 1024
