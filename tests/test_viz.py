import json
from pathlib import Path

import pytest

from warsignal.viz.agent import default_spec
from warsignal.viz.pygame_viz import render


def _result():
    return {
        "mission_id": "MTEST-viz",
        "hypothesis": "Brent and the S&P 500 move together.",
        "plan": {
            "indicator_a": "finance.BZ=F.close",
            "indicator_b": "finance.^GSPC.close",
            "transform_a": "level",
            "transform_b": "level",
            "max_lag_days": 2,
            "event_category": None,
        },
        "stats": {"lagged": {"best_lag": 2, "lags": [-2, 0, 2], "r": [-0.1, 0.2, 0.3]}},
        "scores": {"validity": 5, "interestingness": 6, "unexpectedness": 4},
        "n_obs": 100,
    }


def test_default_spec_has_timeseries():
    spec = default_spec(_result())
    assert spec["panels"][0]["kind"] == "timeseries"
    assert spec["panels"][0]["series"] == ["finance.BZ=F.close", "finance.^GSPC.close"]


def test_headless_render(tmp_path):
    if not Path("data/raw/finance/prices.parquet").exists():
        pytest.skip("finance prices are unavailable")
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps(_result()), encoding="utf-8")
    target = tmp_path / "render.png"
    render(default_spec(_result()), result_path, target, interactive=False)
    assert target.exists()
    assert target.stat().st_size > 10_000
