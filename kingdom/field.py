"""Outdoor field scene: isometric grass field, castle, huts, workers, trees, water."""
from __future__ import annotations

import math

import pygame

from .app import LOGICAL_H, LOGICAL_W, Scene
from .text import draw_text


class FieldScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.castle_rect = pygame.Rect(LOGICAL_W // 2 - 48, LOGICAL_H // 2 - 70, 96, 96)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.castle_rect.collidepoint(event.lpos):
            self.enter_castle()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.enter_castle()

    def enter_castle(self):
        from .castle import CastleScene

        self.app.push(CastleScene(self.app))

    def draw(self, surface, t):
        surface.fill((63, 122, 72))
        castle = self.app.assets.get("castle", (96, 96), (122, 131, 154))
        castle.blit(surface, LOGICAL_W // 2, LOGICAL_H // 2 + 26 + math.sin(t) * 0, t)
        snap = self.app.data.snapshot()
        draw_text(surface, f"active {len(snap.active)}  queue {len(snap.queue)}  done {len(snap.completed)}", (4, 4))
