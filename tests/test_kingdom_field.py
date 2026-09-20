"""Headless tests for the Kingdom field scene."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kingdom.app import App  # noqa: E402
from kingdom.castle import CastleScene  # noqa: E402
from kingdom.field import FieldScene  # noqa: E402


def _make_root(tmp_path: Path) -> Path:
    missions = tmp_path / "missions"
    runs = missions / "runs"
    runs.mkdir(parents=True)
    (missions / "in_progress.txt").write_text(
        "hypothesis one\nhypothesis two\nhypothesis three\n", encoding="utf-8"
    )
    for i, name in enumerate(("20260920-001-alpha", "20260921-002-beta")):
        run = runs / name
        run.mkdir()
        (run / "manifest.json").write_text(
            json.dumps({"hypothesis": f"done {i}", "status": "ok", "mission_id": f"M{i}"}),
            encoding="utf-8",
        )
    return tmp_path


def _make_app(tmp_path: Path) -> App:
    app = App(root=_make_root(tmp_path), scale=2, headless=True, poll_interval=0.0)
    scene = FieldScene(app)
    app.push(scene, fade=False)
    return app


def test_field_renders_and_huts(tmp_path):
    app = _make_app(tmp_path)
    for _ in range(10):
        app.step(1 / 60)
        canvas = app.render()
    scene = app.scene
    assert isinstance(scene, FieldScene)
    assert len(scene.huts) == 3
    colors = set()
    for x in range(0, canvas.get_width(), 24):
        for y in range(0, canvas.get_height(), 24):
            colors.add(canvas.get_at((x, y))[:3])
    assert len(colors) > 1


def test_click_castle_enters(tmp_path):
    app = _make_app(tmp_path)
    for _ in range(5):
        app.step(1 / 60)
        app.render()
    scene = app.scene
    cx, cy = scene._castle_screen()
    scale = app.scale
    pygame.event.post(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(int(cx * scale), int(cy * scale)))
    )
    for _ in range(int(2.0 * 60)):
        app.step(1 / 60)
        app.render()
        if isinstance(app.scene, CastleScene):
            break
    assert isinstance(app.scene, CastleScene)


def test_screenshot_cli(tmp_path):
    out = tmp_path / "field.png"
    subprocess.run(
        [sys.executable, "main.py", "kingdom", "--screenshot", str(out), "--frames", "30"],
        cwd=ROOT,
        check=True,
        timeout=120,
    )
    assert out.is_file() and out.stat().st_size > 0
