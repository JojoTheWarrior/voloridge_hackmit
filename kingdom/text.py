"""Crisp (non-antialiased) pixel text helpers.

Uses ``kingdom/assets/fonts/pixel.ttf`` (any small OFL pixel font) when present,
otherwise the pygame default font rendered without antialiasing.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pygame

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
SIZES = {"small": 8, "normal": 8, "title": 16}


@lru_cache(maxsize=None)
def _font(kind: str) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    size = SIZES.get(kind, 8)
    for candidate in ("pixel.ttf", "pixel.otf"):
        path = FONT_DIR / candidate
        if path.is_file():
            try:
                return pygame.font.Font(str(path), size)
            except pygame.error:
                pass
    return pygame.font.Font(None, size + 4)


def text_size(text: str, kind: str = "normal") -> tuple[int, int]:
    return _font(kind).size(text)


def line_height(kind: str = "normal") -> int:
    return _font(kind).get_linesize()


@lru_cache(maxsize=4096)
def _render(text: str, kind: str, color: tuple) -> pygame.Surface:
    return _font(kind).render(text, False, color)


def draw_text(target: pygame.Surface, text: str, pos: tuple[int, int], color=(238, 240, 244), kind: str = "normal",
              shadow=None, align: str = "left", bold: bool = False) -> pygame.Rect:
    """Blit ``text``; ``bold`` fakes a heavier weight by drawing it twice, 1px apart."""
    surf = _render(text, kind, tuple(color))
    x, y = int(pos[0]), int(pos[1])
    w = surf.get_width() + (1 if bold else 0)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    if shadow is not None:
        target.blit(_render(text, kind, tuple(shadow)), (x + 1, y + 1))
    rect = target.blit(surf, (x, y))
    if bold:
        rect = rect.union(target.blit(surf, (x + 1, y)))
    return rect


def wrap_text(text: str, max_width: int, kind: str = "normal") -> list[str]:
    font = _font(kind)
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = word if not current else current + " " + word
            if font.size(trial)[0] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines
