"""Sprite loading for Kingdom.

``kingdom/assets/manifest.json`` maps sprite names to PNG strips::

    {"sprites": {"castle": {"file": "castle.png", "w": 96, "h": 96,
                            "frames": 1, "anchor": [48, 88]}}}

Frames are laid out left-to-right in a single strip. When a sprite is missing
from the manifest (or the PNG fails to load) a procedural placeholder is drawn
so the game always runs. ``palette.json`` is a list of ``"#rrggbb"`` strings.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pygame

ASSET_DIR = Path(__file__).resolve().parent / "assets"

# Fallback palette (used if palette.json is missing). Calm, low-saturation.
DEFAULT_PALETTE = [
    "#1b1f2a", "#2b3140", "#4a5266", "#7a839a", "#b8c0cf", "#eef0f4",
    "#2f5d3a", "#3f7a48", "#5f9a55", "#8fc06a", "#c7dc8a",
    "#4a3b2a", "#6d5538", "#9a7a4e", "#c9a56d", "#e8d5a3",
    "#1d3f5e", "#2c6486", "#3f8fb3", "#7ac2d8", "#bfe6ef",
    "#7a2f2f", "#b23f3f", "#e06a5a", "#f2a86f", "#f7d98a",
    "#3b2f4a", "#5c4a75", "#8b6fa8", "#b89bd0",
]


def hex_to_rgb(text: str) -> tuple[int, int, int]:
    text = text.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


@dataclass
class Sprite:
    name: str
    frames: list[pygame.Surface]
    anchor: tuple[int, int]
    fps: float = 4.0

    @property
    def w(self) -> int:
        return self.frames[0].get_width()

    @property
    def h(self) -> int:
        return self.frames[0].get_height()

    def frame(self, t: float, offset: float = 0.0) -> pygame.Surface:
        if len(self.frames) == 1:
            return self.frames[0]
        return self.frames[int((t + offset) * self.fps) % len(self.frames)]

    def blit(self, target: pygame.Surface, x: float, y: float, t: float = 0.0, offset: float = 0.0):
        """Blit with the anchor at (x, y) (integer-snapped for crisp pixels)."""
        target.blit(self.frame(t, offset), (int(round(x)) - self.anchor[0], int(round(y)) - self.anchor[1]))


class Assets:
    def __init__(self, asset_dir: Path = ASSET_DIR):
        self.dir = Path(asset_dir)
        self.palette = self._load_palette()
        self.manifest = self._load_manifest()
        self._cache: dict[str, Sprite] = {}

    def _load_palette(self) -> list[tuple[int, int, int]]:
        try:
            raw = json.loads((self.dir / "palette.json").read_text(encoding="utf-8"))
            colors = raw["colors"] if isinstance(raw, dict) else raw
            return [hex_to_rgb(c) for c in colors]
        except (OSError, ValueError, KeyError, TypeError):
            return [hex_to_rgb(c) for c in DEFAULT_PALETTE]

    def _load_manifest(self) -> dict:
        try:
            raw = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
            return raw.get("sprites", {}) if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            return {}

    def has(self, name: str) -> bool:
        return name in self.manifest

    def get(self, name: str, fallback_size: tuple[int, int] = (16, 16), fallback_color=(200, 80, 200)) -> Sprite:
        if name in self._cache:
            return self._cache[name]
        sprite = self._load(name)
        if sprite is None:
            sprite = placeholder(name, fallback_size, fallback_color)
        self._cache[name] = sprite
        return sprite

    def _load(self, name: str) -> Sprite | None:
        entry = self.manifest.get(name)
        if not isinstance(entry, dict):
            return None
        try:
            sheet = pygame.image.load(str(self.dir / entry["file"]))
            if pygame.display.get_init() and pygame.display.get_surface() is not None:
                sheet = sheet.convert_alpha()
        except (OSError, pygame.error, KeyError):
            return None
        w = int(entry.get("w", sheet.get_width()))
        h = int(entry.get("h", sheet.get_height()))
        n = max(1, int(entry.get("frames", max(1, sheet.get_width() // max(1, w)))))
        frames = [sheet.subsurface(pygame.Rect(i * w, 0, w, h)).copy() for i in range(n) if (i + 1) * w <= sheet.get_width()]
        if not frames:
            return None
        anchor = entry.get("anchor", [w // 2, h])
        return Sprite(name, frames, (int(anchor[0]), int(anchor[1])), float(entry.get("fps", 4.0)))


def placeholder(name: str, size: tuple[int, int], color) -> Sprite:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill((*color, 255))
    pygame.draw.rect(surf, (0, 0, 0, 255), surf.get_rect(), 1)
    return Sprite(name, [surf], (size[0] // 2, size[1]))
