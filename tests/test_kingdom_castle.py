import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from kingdom.app import App, Scene  # noqa: E402
from kingdom.castle import COMPLETED, CURRENT, DETAIL, MAIN, QUEUE, CastleScene  # noqa: E402
from kingdom.ui import ScrollList, clean_markdown, clip_lines, fmt_elapsed, signal_color  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def make_root(tmp_path: Path) -> Path:
    missions = tmp_path / "missions"
    runs = missions / "runs"
    runs.mkdir(parents=True)
    (missions / "queue.txt").write_text("Alpha leads beta by two days.\nGamma tracks delta.\nEpsilon is noise.\n")
    (missions / "in_progress.txt").write_text(
        "2026-09-20T01:00:00+00:00 | Iran news volume leads Brent returns during the blockade phases of the war.\n")
    run = runs / "20260920-001-alpha_x_beta"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({
        "mission_id": "M20260920-000001", "hypothesis": "Alpha leads beta by two days.", "status": "ok",
        "n_obs": 42, "r": 0.1234, "perm_p": 0.05, "validity": 6.5, "interestingness": 4.0, "unexpectedness": 3.0,
        "created_at": "2026-09-20T01:10:00+00:00"}))
    (run / "judge.json").write_text(json.dumps({"scores": {"validity": 6.5}}))
    (run / "note.md").write_text("# M20260920-000001\n\n| Field | Value |\n|---|---|\n| n_obs | 42 |\n| r | 0.1234 |\n\n"
                                 "**Verdict:** supported.\n\n" + "Lorem ipsum dolor sit amet. " * 30)
    surf = pygame.Surface((320, 180))
    surf.fill((30, 40, 50))
    pygame.draw.line(surf, (240, 200, 80), (0, 170), (319, 10), 3)
    pygame.image.save(surf, str(run / "viz.png"))
    return tmp_path


@pytest.fixture
def app(tmp_path):
    root = make_root(tmp_path)
    # Keep pygame initialised between tests: kingdom.text caches Font objects and
    # pygame.quit() would invalidate them.
    return App(root=root, headless=True, poll_interval=0.0)


def run_frames(app, scene, n=5, dt=1 / 30):
    for _ in range(n):
        scene.update(dt, app.t)
        app.t += dt
        scene.draw(app.canvas, app.t)
    return app.canvas


@pytest.mark.parametrize("menu", [None, "current", "queue", "completed"])
def test_each_menu_renders(app, menu):
    scene = CastleScene(app, menu=menu)
    app.push(scene, fade=False)
    canvas = run_frames(app, scene, 5)
    assert canvas.get_size() == (480, 270)


def test_detail_view_renders_and_cleans_markdown(app):
    scene = CastleScene(app, menu="completed")
    app.push(scene, fade=False)
    run_frames(app, scene, 2)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
    assert scene.menu == DETAIL
    assert "n_obs: 42" in "\n".join(scene.note_panel.lines)
    assert "Field: Value" not in "\n".join(scene.note_panel.lines)
    run_frames(app, scene, 8)  # covers the 0.2 s slide
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert scene.menu == COMPLETED
    run_frames(app, scene, 8)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert scene.menu == MAIN


def test_elapsed_helper_and_active_card(app):
    assert fmt_elapsed(0) == "00:00"
    assert fmt_elapsed(125.7) == "02:05"
    assert fmt_elapsed(3600) == "60:00"
    scene = CastleScene(app, menu="current")
    app.push(scene, fade=False)
    snap = app.data.snapshot()
    assert len(snap.active) == 1
    assert snap.active[0].elapsed(time.time()) > 0
    run_frames(app, scene, 5)
    assert scene.scroll.content_h > 0


def test_signal_colors_and_clip():
    assert signal_color(0.0) == (178, 63, 63)
    assert signal_color(1.0) == (95, 154, 85)
    assert signal_color(None) == (242, 168, 111)
    pygame.font.init()
    lines = clip_lines("word " * 80, 100, 3)
    assert len(lines) == 3 and lines[-1].endswith("...")
    assert clean_markdown("| a | b |\n|---|---|\n`x`") == "a: b\nx"


def test_scrolling_changes_offset(app):
    scene = CastleScene(app, menu="queue")
    app.push(scene, fade=False)
    run_frames(app, scene, 2)
    # 3 rows fit; force scrollable content
    scene.scroll.set_content_height(1000)
    before = scene.scroll.offset
    scene.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1, x=0, flipped=False, precise_y=-1.0))
    assert scene.scroll.offset > before
    mid = scene.scroll.offset
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN, mod=0))
    assert scene.scroll.offset > mid
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP, mod=0))
    assert scene.scroll.offset < scene.scroll.max_offset
    lst = ScrollList(pygame.Rect(0, 0, 10, 50), step=5)
    lst.set_content_height(200)
    assert lst.scroll_by(1000) and lst.offset == 150
    lst.set_content_height(60)
    assert lst.offset == 10  # clamped, not reset


def test_main_menu_navigation_and_pop(app):
    base = Scene(app)
    app.push(base, fade=False)
    scene = CastleScene(app)
    app.push(scene, fade=False)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0))
    assert scene.selected == 1
    scene.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(0, 0), lpos=scene.buttons[2].rect.center, rel=(0, 0), buttons=(0, 0, 0)))
    assert scene.selected == 2
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0))
    assert scene.menu == COMPLETED
    run_frames(app, scene, 8)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert scene.menu == MAIN
    run_frames(app, scene, 8)
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0))
    assert app.transitioning
    for _ in range(40):
        app.step(1 / 30)
    assert app.scene is base


def test_cli_screenshot(tmp_path):
    root = make_root(tmp_path / "root")
    out = tmp_path / "current.png"
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    subprocess.run([sys.executable, "main.py", "kingdom", "--scene", "current", "--root", str(root),
                    "--screenshot", str(out), "--frames", "10"], cwd=ROOT, check=True, env=env, timeout=120)
    assert out.is_file() and out.stat().st_size > 0
    img = pygame.image.load(str(out))
    assert img.get_size() == (480, 270)
