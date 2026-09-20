"""Small pixel-art widget toolkit for the castle menus.

Everything draws with integer positions onto the 480x270 logical canvas. When a
sprite is missing from the manifest the widgets fall back to ``pygame.draw``
panels (dark wood fill, gold trim, 1px outline) so the menus look tidy even with
placeholder art.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Optional

import pygame

from .assets import Assets, Sprite
from .text import draw_text, line_height, text_size, wrap_text

WOOD = (74, 59, 42)
WOOD_DARK = (52, 40, 28)
GOLD = (201, 165, 109)
GOLD_LIGHT = (232, 213, 163)
OUTLINE = (20, 16, 12)
PARCHMENT = (232, 213, 163)
PARCHMENT_DARK = (154, 122, 78)
INK = (43, 33, 24)
TEXT = (238, 240, 244)
TEXT_DIM = (184, 192, 207)
TEXT_FAINT = (122, 131, 154)
RED = (178, 63, 63)
AMBER = (242, 168, 111)
GREEN = (95, 154, 85)
SHADOW = (27, 31, 42)


def lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def lerp_color(c1, c2, k: float) -> tuple[int, int, int]:
    k = max(0.0, min(1.0, k))
    return tuple(int(round(lerp(c1[i], c2[i], k))) for i in range(3))


def signal_color(signal: Optional[float]) -> tuple[int, int, int]:
    """red (0) -> amber (0.5) -> green (1); amber when unknown."""
    if signal is None:
        return AMBER
    if signal < 0.5:
        return lerp_color(RED, AMBER, signal * 2)
    return lerp_color(AMBER, GREEN, (signal - 0.5) * 2)


def fmt_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def fmt_num(value, digits: int) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _break_word(word: str, max_width: int, kind: str) -> list[str]:
    parts, current = [], ""
    for ch in word:
        if current and text_size(current + ch, kind)[0] > max_width:
            parts.append(current)
            current = ch
        else:
            current += ch
    return parts + [current] if current else parts


def wrap_hard(text: str, max_width: int, kind: str = "normal") -> list[str]:
    """``wrap_text`` that also breaks words wider than ``max_width`` (paths, ids)."""
    words = []
    for word in text.replace("\n", " \n ").split(" "):
        if word and word != "\n" and text_size(word, kind)[0] > max_width:
            words.extend(_break_word(word, max_width, kind))
        else:
            words.append(word)
    return wrap_text(" ".join(words).replace(" \n ", "\n"), max_width, kind)


def clip_lines(text: str, max_width: int, max_lines: int, kind: str = "normal") -> list[str]:
    """Wrap ``text`` and truncate to ``max_lines`` with a trailing ``...``."""
    lines = wrap_hard(text, max_width, kind) if text else [""]
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    last = lines[-1]
    while last and text_size(last + "...", kind)[0] > max_width:
        last = last[:-1].rstrip()
    lines[-1] = last + "..."
    return lines


# --- 9-slice ---------------------------------------------------------------

def draw_nine_slice(target: pygame.Surface, frame: pygame.Surface, rect: pygame.Rect, border: int = 8):
    """Stretch a ``frame`` (corners/edges of ``border`` px) over ``rect``."""
    rect = pygame.Rect(rect)
    fw, fh = frame.get_size()
    b = min(border, fw // 2, fh // 2)
    inner_w = max(0, rect.w - 2 * b)
    inner_h = max(0, rect.h - 2 * b)
    src_w, src_h = fw - 2 * b, fh - 2 * b

    def piece(sx, sy, sw, sh, dx, dy, dw, dh):
        if sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
            return
        part = frame.subsurface(pygame.Rect(sx, sy, sw, sh))
        if (sw, sh) != (dw, dh):
            part = pygame.transform.scale(part, (dw, dh))
        target.blit(part, (dx, dy))

    x, y = rect.x, rect.y
    piece(0, 0, b, b, x, y, b, b)
    piece(fw - b, 0, b, b, x + rect.w - b, y, b, b)
    piece(0, fh - b, b, b, x, y + rect.h - b, b, b)
    piece(fw - b, fh - b, b, b, x + rect.w - b, y + rect.h - b, b, b)
    piece(b, 0, src_w, b, x + b, y, inner_w, b)
    piece(b, fh - b, src_w, b, x + b, y + rect.h - b, inner_w, b)
    piece(0, b, b, src_h, x, y + b, b, inner_h)
    piece(fw - b, b, b, src_h, x + rect.w - b, y + b, b, inner_h)
    piece(b, b, src_w, src_h, x + b, y + b, inner_w, inner_h)


def draw_fallback_panel(target: pygame.Surface, rect: pygame.Rect, fill=WOOD, trim=GOLD, outline=OUTLINE):
    rect = pygame.Rect(rect)
    pygame.draw.rect(target, outline, rect)
    inner = rect.inflate(-2, -2)
    pygame.draw.rect(target, trim, inner)
    pygame.draw.rect(target, fill, inner.inflate(-4, -4))
    # small corner studs
    for cx in (rect.x + 2, rect.right - 4):
        for cy in (rect.y + 2, rect.bottom - 4):
            pygame.draw.rect(target, GOLD_LIGHT if trim == GOLD else outline, (cx, cy, 2, 2))


def draw_panel(target: pygame.Surface, assets: Assets, rect: pygame.Rect, name: str = "panel", frame: int = 0):
    """Draw a 9-slice panel from sprite ``name`` or a procedural fallback."""
    rect = pygame.Rect(rect)
    if assets.has(name):
        sprite = assets.get(name)
        frame = min(frame, len(sprite.frames) - 1)
        draw_nine_slice(target, sprite.frames[frame], rect, 8 if sprite.w >= 24 else 4)
        return
    if name == "panel_light":
        draw_fallback_panel(target, rect, PARCHMENT, PARCHMENT_DARK, INK)
    elif name == "button":
        if frame:
            draw_fallback_panel(target, rect, (109, 85, 56), GOLD_LIGHT, OUTLINE)
        else:
            draw_fallback_panel(target, rect, WOOD_DARK, GOLD, OUTLINE)
    elif name == "bar_frame":
        pygame.draw.rect(target, OUTLINE, rect)
        pygame.draw.rect(target, GOLD, rect.inflate(-2, -2))
        pygame.draw.rect(target, SHADOW, rect.inflate(-4, -4))
    else:
        draw_fallback_panel(target, rect)


def draw_sprite_or_box(target: pygame.Surface, assets: Assets, name: str, x: int, y: int, size: tuple[int, int],
                       t: float = 0.0, color=(201, 165, 109)):
    """Top-left blit of a sprite; a tiny gold glyph box when the art is missing."""
    if assets.has(name):
        sprite = assets.get(name, size)
        target.blit(sprite.frame(t), (int(x), int(y)))
    else:
        rect = pygame.Rect(int(x), int(y), size[0], size[1])
        pygame.draw.rect(target, OUTLINE, rect)
        pygame.draw.rect(target, color, rect.inflate(-2, -2))
        pygame.draw.rect(target, GOLD_LIGHT, (rect.x + 3, rect.y + 3, max(1, rect.w - 6), 1))


# --- widgets ---------------------------------------------------------------

class Button:
    def __init__(self, label: str, rect: pygame.Rect, icon: Optional[str] = None, action=None):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.icon = icon
        self.action = action

    def draw(self, target: pygame.Surface, assets: Assets, selected: bool, t: float, dx: int = 0, dy: int = 0):
        rect = self.rect.move(dx, dy)
        draw_panel(target, assets, rect, "button", 1 if selected else 0)
        tx = rect.x + 12
        if self.icon:
            draw_sprite_or_box(target, assets, self.icon, rect.x + 10, rect.centery - 8, (16, 16), t)
            tx = rect.x + 32
        color = GOLD_LIGHT if selected else TEXT
        draw_text(target, self.label, (tx, rect.centery - text_size(self.label)[1] // 2), color, shadow=OUTLINE)


class ProgressBar:
    @staticmethod
    def draw(target: pygame.Surface, assets: Assets, rect: pygame.Rect, progress: float, color, t: float,
             shimmer: bool = True, pulse: bool = False):
        rect = pygame.Rect(rect)
        draw_panel(target, assets, rect, "bar_frame")
        inner = rect.inflate(-6, -6)
        progress = max(0.0, min(1.0, progress))
        fill_w = int(inner.w * progress)
        if pulse:
            k = 0.5 + 0.5 * math.sin(t * 2.0)
            color = lerp_color(color, GOLD_LIGHT, 0.25 * k)
        if fill_w > 0:
            fill = pygame.Rect(inner.x, inner.y, fill_w, inner.h)
            pygame.draw.rect(target, color, fill)
            pygame.draw.rect(target, lerp_color(color, GOLD_LIGHT, 0.35), (fill.x, fill.y, fill.w, 1))
            if shimmer and fill_w > 6:
                # a slow 3px highlight sweeping along the fill
                phase = (t * 0.25) % 1.0
                sx = fill.x + int(phase * (fill.w - 3))
                pygame.draw.rect(target, lerp_color(color, GOLD_LIGHT, 0.6), (sx, fill.y, 3, fill.h))


class ScrollList:
    """Scroll-offset bookkeeping for a vertical list of rows of varying height.

    ``offset`` is in pixels; ``content_h`` is the total content height. The
    caller draws rows relative to ``-offset`` inside a clipped viewport.
    """

    def __init__(self, viewport: pygame.Rect, step: int = 12):
        self.viewport = pygame.Rect(viewport)
        self.offset = 0
        self.content_h = 0
        self.step = step

    @property
    def max_offset(self) -> int:
        return max(0, self.content_h - self.viewport.h)

    def set_content_height(self, h: int):
        self.content_h = int(h)
        self.offset = max(0, min(self.offset, self.max_offset))

    def scroll_by(self, px: int) -> bool:
        before = self.offset
        self.offset = max(0, min(self.offset + int(px), self.max_offset))
        return self.offset != before

    def scroll_to(self, px: int):
        self.offset = max(0, min(int(px), self.max_offset))

    def ensure_visible(self, top: int, bottom: int):
        if top < self.offset:
            self.offset = top
        elif bottom > self.offset + self.viewport.h:
            self.offset = bottom - self.viewport.h
        self.offset = max(0, min(self.offset, self.max_offset))

    def handle_event(self, event) -> bool:
        """Wheel / arrow / page keys. Returns True if the offset changed."""
        if event.type == pygame.MOUSEWHEEL:
            return self.scroll_by(-event.y * self.step * 2)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            return self.scroll_by(-self.step * 2 if event.button == 4 else self.step * 2)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                return self.scroll_by(-self.step)
            if event.key == pygame.K_DOWN:
                return self.scroll_by(self.step)
            if event.key == pygame.K_PAGEUP:
                return self.scroll_by(-self.viewport.h)
            if event.key == pygame.K_PAGEDOWN:
                return self.scroll_by(self.viewport.h)
            if event.key == pygame.K_HOME:
                return self.scroll_by(-self.content_h)
            if event.key == pygame.K_END:
                return self.scroll_by(self.content_h)
        return False

    def draw_scrollbar(self, target: pygame.Surface, assets: Assets, x: int, t: float = 0.0, dx: int = 0, dy: int = 0):
        if self.max_offset <= 0:
            return
        track = pygame.Rect(x + dx, self.viewport.y + dy + 10, 4, self.viewport.h - 20)
        pygame.draw.rect(target, OUTLINE, track)
        pygame.draw.rect(target, WOOD_DARK, track.inflate(-2, 0))
        thumb_h = max(8, int(track.h * self.viewport.h / max(1, self.content_h)))
        thumb_y = track.y + int((track.h - thumb_h) * self.offset / self.max_offset)
        pygame.draw.rect(target, GOLD, (track.x, thumb_y, 4, thumb_h))
        pygame.draw.rect(target, GOLD_LIGHT, (track.x + 1, thumb_y, 2, 1))
        if self.offset > 0:
            draw_sprite_or_box(target, assets, "arrow_up", track.x - 2, track.y - 10, (8, 8), t)
        if self.offset < self.max_offset:
            draw_sprite_or_box(target, assets, "arrow_down", track.x - 2, track.bottom + 2, (8, 8), t)


class TextPanel:
    """Wrapped, scrollable text (used for notes)."""

    def __init__(self, rect: pygame.Rect, kind: str = "small"):
        self.rect = pygame.Rect(rect)
        self.kind = kind
        self.lines: list[str] = []
        self.scroll = ScrollList(self.rect.inflate(-8, -8), step=line_height(kind))
        self._source: Optional[str] = None

    def set_text(self, text: str):
        if text == self._source:
            return
        self._source = text
        width = self.scroll.viewport.w - 12
        self.lines = []
        for paragraph in clean_markdown(text).split("\n"):
            self.lines.extend(wrap_hard(paragraph, width, self.kind) if paragraph.strip() else [""])
        self.scroll.set_content_height(len(self.lines) * line_height(self.kind))
        self.scroll.scroll_to(0)

    def handle_event(self, event) -> bool:
        return self.scroll.handle_event(event)

    def draw(self, target: pygame.Surface, assets: Assets, color=INK, dx: int = 0, dy: int = 0):
        rect = self.rect.move(dx, dy)
        draw_panel(target, assets, rect, "panel_light")
        view = self.scroll.viewport.move(dx, dy)
        prev = target.get_clip()
        target.set_clip(view.clip(prev) if prev else view)
        lh = line_height(self.kind)
        first = self.scroll.offset // lh
        y = view.y - (self.scroll.offset % lh)
        for line in self.lines[first:first + view.h // lh + 2]:
            draw_text(target, line, (view.x, y), color, kind=self.kind)
            y += lh
        target.set_clip(prev)
        self.scroll.draw_scrollbar(target, assets, rect.right - 7, dx=0, dy=0)


def clean_markdown(text: str) -> str:
    """Light markdown cleanup: ``| a | b |`` rows -> ``a: b``, drop rules/backticks/#."""
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator row
            if len(cells) >= 2 and cells[0].lower() == "field" and cells[1].lower() == "value":
                continue  # header row
            line = ": ".join(c for c in cells if c) if len(cells) > 1 else cells[0]
        line = line.replace("`", "").replace("**", "")
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        out.append(line)
    return "\n".join(out)


class ThumbnailCache:
    """Loads and scales viz PNGs once per (path, size)."""

    def __init__(self):
        self._cache: dict[tuple[str, tuple[int, int]], Optional[pygame.Surface]] = {}

    def get(self, path: Optional[Path], size: tuple[int, int]) -> Optional[pygame.Surface]:
        if path is None:
            return None
        key = (str(path), size)
        if key in self._cache:
            return self._cache[key]
        surf: Optional[pygame.Surface] = None
        try:
            img = pygame.image.load(str(path))
            surf = pygame.transform.smoothscale(img, size) if img.get_bitsize() >= 24 else pygame.transform.scale(img, size)
            surf = quantize(surf)
        except (OSError, pygame.error, ValueError):
            surf = None
        self._cache[key] = surf
        return surf


def quantize(surface: pygame.Surface, levels: int = 6) -> pygame.Surface:
    """Posterize a small surface so smoothscaled thumbnails read as pixel art."""
    out = surface.convert(24) if surface.get_bitsize() != 24 else surface
    step = 255 / (levels - 1)
    arr = pygame.PixelArray(out)
    w, h = out.get_size()
    for x in range(w):
        for y in range(h):
            r, g, b, _ = out.unmap_rgb(arr[x, y])
            arr[x, y] = (int(round(r / step) * step), int(round(g / step) * step), int(round(b / step) * step))
    arr.close()
    return out


def draw_thumbnail(target: pygame.Surface, thumb: Optional[pygame.Surface], x: int, y: int, size: tuple[int, int]):
    rect = pygame.Rect(int(x), int(y), size[0], size[1])
    pygame.draw.rect(target, OUTLINE, rect.inflate(2, 2))
    if thumb is not None:
        target.blit(thumb, rect.topleft)
    else:
        pygame.draw.rect(target, SHADOW, rect)
        pygame.draw.line(target, WOOD, rect.topleft, rect.bottomright)
        pygame.draw.line(target, WOOD, rect.topright, rect.bottomleft)


def draw_cursor_hand(target: pygame.Surface, assets: Assets, x: int, y: int, t: float):
    """Pointing hand (bobbing) with its tip at (x, y)."""
    bob = int(round(math.sin(t * 3) * 1.5))
    if assets.has("cursor_hand"):
        sprite = assets.get("cursor_hand", (8, 8))
        target.blit(sprite.frame(t), (int(x) - 8 + bob, int(y) - 4))
    else:
        px, py = int(x) - 8 + bob, int(y) - 3
        pts = [(px, py), (px + 6, py + 3), (px, py + 6)]
        pygame.draw.polygon(target, OUTLINE, [(a - 1, b) for a, b in pts])
        pygame.draw.polygon(target, GOLD_LIGHT, pts)
