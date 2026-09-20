"""Kingdom application shell: fixed 480x270 logical canvas, integer upscale,
scene stack with fade transitions, headless screenshot support.

    python main.py kingdom [--scale N] [--screenshot out.png] [--frames N] [--scene field|castle|...]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from .assets import Assets  # noqa: E402
from .data import DataAdapter  # noqa: E402

LOGICAL_W, LOGICAL_H = 480, 270
ROOT = Path(__file__).resolve().parents[1]


class Scene:
    """Base scene. ``app`` gives access to ``assets``, ``data``, ``push``/``pop``."""

    def __init__(self, app: "App"):
        self.app = app

    def on_enter(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float, t: float):
        pass

    def draw(self, surface: pygame.Surface, t: float):
        pass


class App:
    def __init__(self, root: Path = ROOT, scale: int = 2, headless: bool = False, poll_interval: float = 2.0):
        self.root = Path(root)
        self.headless = headless
        if headless:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.init()
        pygame.font.init()
        self.scale = max(1, int(scale))
        flags = 0 if headless else pygame.RESIZABLE
        self.window = pygame.display.set_mode((LOGICAL_W * self.scale, LOGICAL_H * self.scale), flags)
        pygame.display.set_caption("Kingdom")
        self.canvas = pygame.Surface((LOGICAL_W, LOGICAL_H)).convert()
        self.assets = Assets()
        self.data = DataAdapter(self.root, poll_interval=poll_interval)
        self.scenes: list[Scene] = []
        self.clock = pygame.time.Clock()
        self.running = True
        self.t = 0.0
        # transition: (kind, progress, pending_action)
        self._fade = 0.0  # 0 = clear, 1 = black
        self._fade_dir = 0
        self._pending = None

    # -- scene stack -------------------------------------------------------
    @property
    def scene(self) -> Scene | None:
        return self.scenes[-1] if self.scenes else None

    def push(self, scene: Scene, fade: bool = True):
        if fade:
            self._queue(lambda: self._push_now(scene))
        else:
            self._push_now(scene)

    def pop(self, fade: bool = True):
        if fade:
            self._queue(self._pop_now)
        else:
            self._pop_now()

    def _push_now(self, scene: Scene):
        self.scenes.append(scene)
        scene.on_enter()

    def _pop_now(self):
        if len(self.scenes) > 1:
            self.scenes.pop()
            self.scene.on_enter()

    def _queue(self, action):
        self._pending = action
        self._fade_dir = 1

    @property
    def transitioning(self) -> bool:
        return self._fade_dir != 0

    # -- loop --------------------------------------------------------------
    def logical_mouse(self, pos) -> tuple[int, int]:
        ox, oy, sc = self._viewport()
        return int((pos[0] - ox) / sc), int((pos[1] - oy) / sc)

    def _viewport(self) -> tuple[int, int, int]:
        ww, wh = self.window.get_size()
        sc = max(1, min(ww // LOGICAL_W, wh // LOGICAL_H))
        return (ww - LOGICAL_W * sc) // 2, (wh - LOGICAL_H * sc) // 2, sc

    def step(self, dt: float):
        self.t += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_q and (event.mod & pygame.KMOD_CTRL):
                self.running = False
            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                event.dict["lpos"] = self.logical_mouse(event.pos)
                if not self.transitioning and self.scene:
                    self.scene.handle_event(event)
            elif not self.transitioning and self.scene:
                self.scene.handle_event(event)
        if self._fade_dir:
            self._fade += self._fade_dir * dt * 2.5
            if self._fade >= 1.0 and self._pending:
                self._fade = 1.0
                action, self._pending = self._pending, None
                action()
                self._fade_dir = -1
            elif self._fade <= 0.0:
                self._fade = 0.0
                self._fade_dir = 0
        if self.scene:
            self.scene.update(dt, self.t)

    def render(self) -> pygame.Surface:
        if self.scene:
            self.scene.draw(self.canvas, self.t)
        if self._fade > 0:
            shade = pygame.Surface(self.canvas.get_size())
            shade.fill((10, 12, 18))
            shade.set_alpha(int(255 * min(1.0, self._fade)))
            self.canvas.blit(shade, (0, 0))
        ox, oy, sc = self._viewport()
        self.window.fill((10, 12, 18))
        if sc == 1:
            self.window.blit(self.canvas, (ox, oy))
        else:
            self.window.blit(pygame.transform.scale(self.canvas, (LOGICAL_W * sc, LOGICAL_H * sc)), (ox, oy))
        pygame.display.flip()
        return self.canvas

    def run(self, max_frames: int | None = None, screenshot: Path | None = None, fixed_dt: float | None = None):
        frames = 0
        while self.running and (max_frames is None or frames < max_frames):
            dt = fixed_dt if fixed_dt is not None else min(0.05, self.clock.tick(60) / 1000.0)
            if fixed_dt is not None:
                self.clock.tick(60 if not self.headless else 0)
            self.step(dt)
            self.render()
            frames += 1
        if screenshot is not None:
            pygame.image.save(self.canvas, str(screenshot))
        pygame.quit()


def make_scene(app: App, name: str) -> Scene:
    from .field import FieldScene

    if name == "field":
        return FieldScene(app)
    from .castle import CastleScene

    return CastleScene(app, menu=None if name == "castle" else name)


def parse_args(argv) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="kingdom")
    parser.add_argument("--scale", type=int, default=3)
    parser.add_argument("--screenshot", type=Path, help="render headlessly and save the final frame")
    parser.add_argument("--frames", type=int, default=None, help="stop after N frames")
    parser.add_argument("--scene", default="field", help="field | castle | current | queue | completed")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT, help="repo root containing missions/")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    headless = args.headless or args.screenshot is not None
    app = App(root=args.root, scale=args.scale, headless=headless)
    app.push(make_scene(app, args.scene), fade=False)
    frames = args.frames if args.frames is not None else (120 if headless else None)
    app.run(max_frames=frames, screenshot=args.screenshot, fixed_dt=1 / 60 if headless else None)


if __name__ == "__main__":
    main()
