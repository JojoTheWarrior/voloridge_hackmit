"""Castle interior: great hall + menus (current missions, queue, completed).

Contract with the rest of Kingdom:

* ``CastleScene(app, menu=None)`` — ``menu`` may be ``"current"``,
  ``"queue"`` or ``"completed"`` to open directly on that menu (used by
  ``--scene`` and screenshot tests); ``None`` shows the main menu.
* Esc/Backspace at the main menu calls ``app.pop()`` (App fades back to the field).
* Data comes from ``app.data.snapshot()`` (see ``kingdom/data.py``).
* Sprites come from ``app.assets.get(name)``; text from ``kingdom.text``.
"""
from __future__ import annotations

import pygame

from .app import LOGICAL_H, LOGICAL_W, Scene
from .text import draw_text


class CastleScene(Scene):
    def __init__(self, app, menu: str | None = None):
        super().__init__(app)
        self.menu = menu

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.pop()

    def draw(self, surface, t):
        surface.fill((43, 49, 64))
        draw_text(surface, "GREAT HALL (placeholder)", (LOGICAL_W // 2, LOGICAL_H // 2 - 8), align="center")
        draw_text(surface, "Esc: back", (LOGICAL_W // 2, LOGICAL_H // 2 + 8), (184, 192, 207), align="center")
