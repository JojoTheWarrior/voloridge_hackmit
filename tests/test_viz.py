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


def test_default_spec_panels_follow_standard_contract():
    spec = default_spec(_result())
    kinds = [panel["kind"] for panel in spec["panels"]]
    assert kinds == ["timeseries", "lagcorr", "scatter"]
    assert all(panel["note"] for panel in spec["panels"])
    assert "+2d" in spec["panels"][1]["note"]


def test_bundled_fonts_load():
    import pygame

    from warsignal.viz.style import FONT_DIR, FONT_FILES, load_fonts

    assert all((FONT_DIR / name).exists() for name in FONT_FILES.values())
    pygame.init()
    fonts = load_fonts(pygame)
    for role in ("verdict", "title", "h", "hi", "mono", "monobold", "small"):
        assert role in fonts
    assert fonts["title"].size("WarSignal")[0] > fonts["small"].size("WarSignal")[0]


@pytest.mark.parametrize(
    "result, expected",
    [
        ({"status": "failed"}, "FAILED"),
        ({"scores": {"validity": 1.0, "supported_prob": 0.1}}, "NOISE"),
        ({"scores": {"validity": 3.9, "supported_prob": 0.03}, "stats": {"perm_p": 0.12}}, "WEAK"),
        ({"scores": {"validity": 6.0, "supported_prob": 0.6}, "stats": {"perm_p": 0.3}}, "WEAK"),
        ({"scores": {"validity": 6.5, "supported_prob": 0.6}, "stats": {"perm_p": 0.01}}, "SIGNAL"),
        ({"scores": {"validity": 9.0, "supported_prob": 0.9}, "stats": {"perm_p": 0.001}}, "STRONG SIGNAL"),
    ],
)
def test_verdict_tiers(result, expected):
    from warsignal.viz.style import verdict_tier

    assert verdict_tier(result)[1] == expected


def test_lag_axis_scales_to_observed_peak(tmp_path):
    """Bars for |r| <= 0.11 must fill a large share of the panel, not sit against a fixed +-1 axis."""
    import numpy as np
    import pygame

    from warsignal.viz import pygame_viz
    from warsignal.viz.style import PALETTE, load_fonts

    pygame.init()
    fonts = load_fonts(pygame)
    surface = pygame.Surface((pygame_viz.WIDTH, 300))
    surface.fill(PALETTE["bg"])
    rect = pygame.Rect(pygame_viz.PLOT_LEFT, 40, pygame_viz.PLOT_RIGHT - pygame_viz.PLOT_LEFT, 200)
    result = {"stats": {"lagged": {"lags": [-2, -1, 0, 1, 2], "r": [0.02, -0.05, 0.11, 0.04, -0.01],
                                   "best_lag": 0, "best_r": 0.11}}}
    pygame_viz._draw_lagcorr(surface, pygame, fonts, rect, {"series": ["a", "b"]}, result)
    pixels = pygame.surfarray.array3d(surface)
    bar_color = np.array(PALETTE["series"][1])
    mask = np.all(pixels == bar_color, axis=-1)
    ys = np.where(mask.any(axis=0))[0]
    assert ys.size > 0
    tallest = rect.centery - ys.min()
    assert tallest > rect.height * 0.3
