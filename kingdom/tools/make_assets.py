"""Kingdom asset pipeline.

Turns raw generated pictures in ``kingdom/tools/raw/`` (chroma-keyed on
magenta) into crisp palette-locked pixel-art strips in ``kingdom/assets/``, and
draws hand-coded procedural sprites for everything that has no raw source.

    python -m kingdom.tools.make_assets --all
    python -m kingdom.tools.make_assets --only castle,hut
    python -m kingdom.tools.make_assets --all --procedural      # no raw sources at all
    python -m kingdom.tools.make_assets --all --contact-sheet /tmp/sheet.png

Every sprite is a horizontal strip (frames left to right) described in
``manifest.json``; colours are snapped to ``palette.json``; alpha is 0/255.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

TOOLS_DIR = Path(__file__).resolve().parent
RAW_DIR = TOOLS_DIR / "raw"
ASSET_DIR = TOOLS_DIR.parent / "assets"

# --------------------------------------------------------------------------------------
# Palette (calm / low saturation, ~40 colours)
# --------------------------------------------------------------------------------------
PALETTE: dict[str, str] = {
    "black": "#1b1f2a", "navy": "#2b3140", "slate": "#4a5266", "grey": "#7a839a",
    "silver": "#b8c0cf", "white": "#eef0f4",
    "stone_dk": "#6e6a66", "stone_md": "#87817a", "stone": "#9c9691", "stone_lt": "#c4bdb4", "stone_pale": "#e2dcd2",
    "green_dk": "#2f5d3a", "green": "#3f7a48", "green_md": "#5f9a55", "green_lt": "#8fc06a",
    "green_pale": "#c7dc8a", "pine_dk": "#2d4f45", "pine": "#3f6e5c", "pine_lt": "#6f9a7c",
    "brown_dk": "#4a3b2a", "wood": "#7c4b2c", "brown": "#6d5538", "brown_lt": "#9a7a4e", "tan": "#c9a56d",
    "cream": "#e8d5a3", "parchment": "#f1e6c8",
    "blue_dk": "#1d3f5e", "blue": "#2c6486", "blue_md": "#3f8fb3", "blue_lt": "#7ac2d8",
    "blue_pale": "#bfe6ef", "roof_blue": "#4a5a8a",
    "red_dk": "#7a2f2f", "red": "#b23f3f", "orange": "#e06a5a", "peach": "#f2a86f",
    "gold": "#f7d98a", "gold_dk": "#c9962e", "flame": "#f0a030", "tile_red": "#a85a3a",
    "plum_dk": "#3b2f4a", "plum": "#5c4a75",
}


def hex_to_rgb(text: str) -> tuple[int, int, int]:
    text = text.lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


C = {name: hex_to_rgb(value) for name, value in PALETTE.items()}
PAL_ARRAY = np.array(list(C.values()), dtype=np.int32)  # (P, 3)


def quantize_rgb(rgb: np.ndarray) -> np.ndarray:
    """Map an (N, 3) uint8 array to palette indices (nearest colour)."""
    flat = rgb.reshape(-1, 3).astype(np.int32)
    idx = np.empty(flat.shape[0], dtype=np.int32)
    step = 262144
    for start in range(0, flat.shape[0], step):
        chunk = flat[start:start + step]
        d = ((chunk[:, None, :] - PAL_ARRAY[None, :, :]) ** 2).sum(-1)
        idx[start:start + step] = d.argmin(1)
    return idx.reshape(rgb.shape[:-1])


# --------------------------------------------------------------------------------------
# Sprite specs
# --------------------------------------------------------------------------------------
@dataclass
class Raw:
    file: str
    split: int = 1                     # number of side-by-side frames in the source
    fit: tuple[int, int] | None = None  # box the content is scaled to fit (default: w, h)
    bottom: int | None = None          # y of content bottom edge inside the frame (default: h)
    center_y: bool = False             # centre vertically instead of bottom-aligning
    stretch: bool = False              # ignore aspect ratio and fill the frame (backgrounds)
    crop: tuple[float, float, float, float] | None = None  # fractional crop l, t, r, b before keying
    same_scale_as: str | None = None   # reuse another sprite's placement (castle_gate_open)


@dataclass
class Spec:
    w: int
    h: int
    frames: int = 1
    anchor: tuple[int, int] | None = None
    fps: float = 4.0
    raw: Raw | None = None
    proc: Callable[["Spec"], list[Image.Image]] | None = None

    def anchor_or_default(self) -> tuple[int, int]:
        return self.anchor if self.anchor is not None else (self.w // 2, self.h)


SPECS: dict[str, Spec] = {}
PROC: dict[str, Callable[[Spec], list[Image.Image]]] = {}


def procedural(name: str):
    def deco(fn):
        PROC[name] = fn
        return fn
    return deco


# --------------------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------------------
def new(w: int, h: int) -> Image.Image:
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def rgba(name: str) -> tuple[int, int, int, int]:
    return (*C[name], 255)


def px(img: Image.Image, x: int, y: int, c: str):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((x, y), rgba(c))


def rect(img: Image.Image, x0: int, y0: int, x1: int, y1: int, c: str, outline: str | None = None):
    """Filled rectangle, inclusive coordinates."""
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=rgba(c), outline=rgba(outline) if outline else None)


def hline(img, x0, x1, y, c):
    rect(img, min(x0, x1), y, max(x0, x1), y, c)


def vline(img, x, y0, y1, c):
    rect(img, x, min(y0, y1), x, max(y0, y1), c)


def line(img, x0, y0, x1, y1, c):
    ImageDraw.Draw(img).line([x0, y0, x1, y1], fill=rgba(c), width=1)


def ellipse(img, x0, y0, x1, y1, c, outline: str | None = None):
    ImageDraw.Draw(img).ellipse([x0, y0, x1, y1], fill=rgba(c), outline=rgba(outline) if outline else None)


def poly(img, pts, c, outline: str | None = None):
    ImageDraw.Draw(img).polygon(pts, fill=rgba(c), outline=rgba(outline) if outline else None)


def outline_alpha(img: Image.Image, c: str = "black") -> Image.Image:
    """Add a 1px outline of colour c around every opaque region (inside the canvas)."""
    a = np.array(img)[:, :, 3] > 0
    grown = a.copy()
    grown[1:, :] |= a[:-1, :]
    grown[:-1, :] |= a[1:, :]
    grown[:, 1:] |= a[:, :-1]
    grown[:, :-1] |= a[:, 1:]
    edge = grown & ~a
    arr = np.array(img)
    arr[edge] = (*C[c], 255)
    return Image.fromarray(arr, "RGBA")


def iso_mask(w: int = 32, h: int = 16) -> np.ndarray:
    """2:1 diamond mask. Rows grow by 4 px per row so 32x16 tiles butt seamlessly."""
    m = np.zeros((h, w), dtype=bool)
    half = h // 2
    for r in range(half):
        span = (r + 1) * (w // h)  # 2 px per side per row
        m[r, w // 2 - span: w // 2 + span] = True
        m[h - 1 - r, w // 2 - span: w // 2 + span] = True
    return m


def iso_tile(base: str, w: int = 32, h: int = 16) -> Image.Image:
    img = new(w, h)
    m = iso_mask(w, h)
    arr = np.array(img)
    arr[m] = (*C[base], 255)
    return Image.fromarray(arr, "RGBA")


def speckle(img: Image.Image, colours: list[str], n: int, seed: int, mask: np.ndarray | None = None):
    rng = random.Random(seed)
    w, h = img.size
    placed = 0
    tries = 0
    while placed < n and tries < n * 50:
        tries += 1
        x, y = rng.randrange(w), rng.randrange(h)
        if mask is not None and not mask[y, x]:
            continue
        px(img, x, y, rng.choice(colours))
        placed += 1


def nine_slice_frame(w: int, h: int, fill: str, edge: str, trim: str, dark: str, corner_gem: str | None = None):
    img = new(w, h)
    rect(img, 0, 0, w - 1, h - 1, fill)
    rect(img, 0, 0, w - 1, h - 1, fill, outline=dark)      # outer dark line
    rect(img, 1, 1, w - 2, h - 2, fill, outline=trim)      # gold trim
    rect(img, 2, 2, w - 3, h - 3, fill, outline=edge)      # inner edge
    rect(img, 3, 3, w - 4, h - 4, fill)
    if corner_gem:
        for (x, y) in [(1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)]:
            px(img, x, y, corner_gem)
    return img


# --------------------------------------------------------------------------------------
# Procedural sprites: field tiles
# --------------------------------------------------------------------------------------
@procedural("grass")
def _grass(spec: Spec):
    frames = []
    m = iso_mask()
    for i in range(spec.frames):
        img = iso_tile("green")
        speckle(img, ["green_md", "green_md", "green_dk"], 10 + i * 3, seed=10 + i, mask=m)
        speckle(img, ["green_lt"], 2 + i, seed=50 + i, mask=m)
        frames.append(img)
    return frames


@procedural("grass_flowers")
def _grass_flowers(spec: Spec):
    img = iso_tile("green")
    m = iso_mask()
    speckle(img, ["green_md", "green_dk"], 8, seed=7, mask=m)
    rng = random.Random(3)
    colours = ["gold", "white", "orange", "blue_pale", "peach"]
    for k in range(5):
        for _ in range(40):
            x, y = rng.randrange(3, 29), rng.randrange(2, 14)
            if m[y, x] and m[y, x - 1] and m[y, x + 1]:
                px(img, x, y, colours[k % len(colours)])
                px(img, x - 1, y + 1, "green_lt")
                break
    return [img]


@procedural("path")
def _path(spec: Spec):
    img = iso_tile("tan")
    m = iso_mask()
    speckle(img, ["brown_lt", "cream"], 14, seed=21, mask=m)
    # small pebbles
    for (x, y) in [(9, 8), (21, 5), (16, 11), (25, 9)]:
        px(img, x, y, "stone")
        px(img, x + 1, y, "stone_lt")
    return [img]


@procedural("field_crop")
def _field_crop(spec: Spec):
    frames = []
    m = iso_mask()
    for v in range(spec.frames):
        img = iso_tile("brown")
        arr = np.array(img)
        for y in range(16):
            for x in range(32):
                if not m[y, x]:
                    continue
                # furrows run along one diamond axis: x - 2y (v=0) or x + 2y (v=1)
                k = (x - 2 * y) if v == 0 else (x + 2 * y)
                if k % 6 in (0, 1):
                    arr[y, x] = (*C["brown_dk"], 255)
                elif k % 6 == 3:
                    arr[y, x] = (*C["green_md" if (x + y) % 2 else "green_lt"], 255)
        frames.append(Image.fromarray(arr, "RGBA"))
    return frames


def _water_frame(phase: int) -> Image.Image:
    img = iso_tile("blue_md")
    m = iso_mask()
    arr = np.array(img)
    for y in range(16):
        for x in range(32):
            if not m[y, x]:
                continue
            k = (x // 2 + y + phase) % 8
            if k == 0:
                arr[y, x] = (*C["blue_lt"], 255)
            elif k == 4 and (x + y) % 3 == 0:
                arr[y, x] = (*C["blue"], 255)
    return Image.fromarray(arr, "RGBA")


@procedural("water")
def _water(spec: Spec):
    return [_water_frame(p * 2) for p in range(spec.frames)]


@procedural("shore")
def _shore(spec: Spec):
    """Water tile with a grass+sand edge on one diamond side. Frames: 0=N (top-left edge),
    1=E (top-right), 2=S (bottom-right), 3=W (bottom-left)."""
    frames = []
    m = iso_mask()
    for side in range(4):
        img = _water_frame(0)
        arr = np.array(img)
        for y in range(16):
            for x in range(32):
                if not m[y, x]:
                    continue
                # distance (in rows) from each diamond edge
                dx = abs(x - 15.5)
                dy = abs(y - 7.5)
                # edge membership by quadrant
                top = y < 8
                left = x < 16
                on = {0: top and left, 1: top and not left, 2: not top and not left, 3: not top and left}[side]
                depth = 8 - (dx / 2 + dy)  # 0 at edge, ~8 at centre
                if on and depth < 2.0:
                    arr[y, x] = (*C["green"], 255)
                elif on and depth < 3.0:
                    arr[y, x] = (*C["cream"], 255)
                elif on and depth < 4.0:
                    arr[y, x] = (*C["blue_pale"], 255)
        frames.append(Image.fromarray(arr, "RGBA"))
    return frames


# --------------------------------------------------------------------------------------
# Procedural sprites: buildings (fallbacks) and props
# --------------------------------------------------------------------------------------
def _crenellate(img, x0, x1, y, c, dark):
    for x in range(x0, x1 + 1, 2):
        px(img, x, y, c)
    hline(img, x0, x1, y + 1, dark)


def _tower(img, x, y_top, w, h, roof: bool, roof_c="roof_blue"):
    rect(img, x, y_top, x + w - 1, y_top + h - 1, "stone_lt", outline="black")
    for yy in range(y_top + 3, y_top + h - 1, 4):
        for xx in range(x + 1 + (yy // 4 % 2) * 2, x + w - 1, 4):
            px(img, xx, yy, "stone")
    if roof:
        apex = y_top - w // 2 - 2
        poly(img, [(x - 1, y_top), (x + w, y_top), (x + w // 2, apex)], roof_c, outline="black")
        px(img, x + w // 2, apex - 1, "gold")
    else:
        _crenellate(img, x, x + w - 1, y_top - 1, "stone_lt", "black")
    rect(img, x + w // 2 - 1, y_top + 5, x + w // 2, y_top + 8, "black")


def _castle_body(spec: Spec, gate_open: bool) -> Image.Image:
    img = new(spec.w, spec.h)
    # grass mound
    ellipse(img, 8, 104, 119, 122, "green_md", outline="green_dk")
    # walls
    rect(img, 20, 60, 107, 112, "stone_lt", outline="black")
    for yy in range(63, 111, 4):
        for xx in range(22 + (yy // 4 % 2) * 2, 106, 4):
            px(img, xx, yy, "stone")
    _crenellate(img, 20, 107, 58, "stone_lt", "black")
    # towers
    _tower(img, 10, 48, 20, 66, roof=True)
    _tower(img, 98, 48, 20, 66, roof=True)
    _tower(img, 50, 22, 28, 92, roof=False)
    # flag on keep
    vline(img, 64, 6, 22, "brown_dk")
    poly(img, [(65, 7), (78, 10), (65, 14)], "red", outline="red_dk")
    # gate arch
    rect(img, 54, 84, 73, 112, "stone_dk", outline="black")
    ellipse(img, 54, 78, 73, 92, "stone_dk", outline="black")
    if gate_open:
        rect(img, 57, 86, 70, 112, "black")
        ellipse(img, 57, 81, 70, 92, "black")
        rect(img, 60, 92, 67, 112, "flame")
        rect(img, 62, 98, 65, 112, "gold")
        rect(img, 57, 90, 58, 112, "brown")
        rect(img, 69, 90, 70, 112, "brown")
    else:
        rect(img, 57, 86, 70, 112, "brown")
        ellipse(img, 57, 81, 70, 92, "brown")
        for xx in (60, 64, 68):
            vline(img, xx, 84, 112, "brown_dk")
        hline(img, 57, 70, 96, "slate")
        hline(img, 57, 70, 105, "slate")
    return img


@procedural("castle")
def _castle(spec: Spec):
    return [_castle_body(spec, False)]


@procedural("castle_gate_open")
def _castle_open(spec: Spec):
    return [_castle_body(spec, True)]


@procedural("hut")
def _hut(spec: Spec):
    frames = []
    for v in range(spec.frames):
        img = new(spec.w, spec.h)
        wall = "brown_lt" if v == 0 else "cream"
        roof = "tan" if v == 0 else "tile_red"
        rect(img, 5, 16, 26, 28, wall, outline="black")
        poly(img, [(2, 17), (29, 17), (16, 5)], roof, outline="black")
        hline(img, 4, 27, 16, "brown_dk")
        rect(img, 13, 20, 18, 28, "brown_dk", outline="black")
        rect(img, 21, 19, 24, 22, "blue_pale", outline="black")
        if v == 1:
            rect(img, 21, 8, 23, 13, "stone", outline="black")
            for yy in range(7, 16, 2):
                hline(img, 4 + (16 - yy) // 2, 28 - (16 - yy) // 2, yy, "brown")
        frames.append(img)
    return frames


@procedural("workshop")
def _workshop(spec: Spec):
    img = new(spec.w, spec.h)
    rect(img, 3, 18, 44, 38, "stone", outline="black")
    rect(img, 3, 12, 44, 18, "brown_lt", outline="black")
    poly(img, [(0, 13), (47, 13), (24, 2)], "slate", outline="black")
    rect(img, 34, 3, 38, 12, "stone_dk", outline="black")
    rect(img, 8, 20, 22, 38, "brown_dk", outline="black")   # open front
    rect(img, 11, 27, 18, 33, "flame")
    rect(img, 13, 30, 16, 33, "gold")
    rect(img, 28, 24, 36, 30, "blue_pale", outline="black")
    rect(img, 38, 30, 44, 38, "navy")
    return [img]


def _worker_frame(i: int, tunic: str, skin: str = "peach") -> Image.Image:
    img = new(16, 16)
    step = i % 2
    # legs
    if i % 2 == 0:
        rect(img, 6, 12, 7, 15, "brown_dk")
        rect(img, 9, 12, 10, 15, "brown_dk")
    else:
        rect(img, 5, 12, 6, 15, "brown_dk")
        rect(img, 10, 12, 11, 15, "brown_dk")
    # body
    rect(img, 5, 7, 10, 11, tunic, outline="black")
    # head
    rect(img, 6, 3, 9, 6, skin, outline="black")
    rect(img, 5, 2, 10, 3, "tan")  # straw hat
    hline(img, 6, 9, 1, "tan")
    px(img, 7, 4, "black")
    # arm + hammer: raised on frames 0,1, down on 2,3
    if i < 2:
        rect(img, 11, 5 - step, 12, 8, skin)
        rect(img, 12, 2 - step, 14, 3 - step, "slate")
        vline(img, 13, 3 - step, 5 - step, "brown")
    else:
        rect(img, 11, 8, 13, 9, skin)
        vline(img, 14, 8, 11, "brown")
        rect(img, 13, 11, 15, 12, "slate")
    return outline_alpha(img)


@procedural("worker")
def _worker(spec: Spec):
    return [_worker_frame(i, "blue") for i in range(spec.frames)]


@procedural("worker_b")
def _worker_b(spec: Spec):
    return [_worker_frame(i, "red") for i in range(spec.frames)]


@procedural("tree")
def _tree(spec: Spec):
    frames = []
    shapes = [
        [(3, 4, 20, 22)],
        [(2, 8, 15, 22), (9, 2, 21, 16)],
        [(1, 10, 22, 22), (6, 4, 18, 14)],
    ]
    for v in range(spec.frames):
        img = new(spec.w, spec.h)
        rect(img, 10, 22, 13, 30, "brown", outline="brown_dk")
        for (x0, y0, x1, y1) in shapes[v]:
            ellipse(img, x0, y0, x1, y1, "green_md")
        for (x0, y0, x1, y1) in shapes[v]:
            ellipse(img, x0 + 2, y0 + 1, x0 + (x1 - x0) // 2 + 1, y0 + (y1 - y0) // 2, "green_lt")
            ellipse(img, x0 + 3, y0 + (y1 - y0) * 2 // 3, x1 - 2, y1 - 1, "green")
        frames.append(outline_alpha(img))
    return frames


@procedural("pine")
def _pine(spec: Spec):
    img = new(spec.w, spec.h)
    rect(img, 10, 32, 13, 38, "brown", outline="brown_dk")
    for k, (top, half) in enumerate([(2, 5), (10, 8), (20, 11)]):
        bottom = top + 12
        poly(img, [(12, top), (12 - half, bottom), (12 + half, bottom)], "pine")
        poly(img, [(12, top + 1), (12 - half + 2, bottom - 1), (12, bottom - 1)], "pine_lt")
    return [outline_alpha(img, "pine_dk")]


@procedural("bush")
def _bush(spec: Spec):
    img = new(spec.w, spec.h)
    ellipse(img, 1, 3, 14, 11, "green_md")
    ellipse(img, 4, 1, 12, 7, "green_md")
    ellipse(img, 5, 2, 9, 5, "green_lt")
    ellipse(img, 3, 8, 13, 11, "green")
    return [outline_alpha(img, "green_dk")]


@procedural("rock")
def _rock(spec: Spec):
    img = new(spec.w, spec.h)
    ellipse(img, 1, 3, 10, 9, "stone")
    ellipse(img, 7, 1, 14, 8, "stone")
    ellipse(img, 3, 3, 7, 5, "stone_lt")
    ellipse(img, 9, 2, 12, 4, "stone_lt")
    ellipse(img, 2, 7, 13, 9, "stone_dk")
    return [outline_alpha(img)]


@procedural("flag")
def _flag(spec: Spec):
    frames = []
    for i in range(spec.frames):
        img = new(spec.w, spec.h)
        vline(img, 1, 0, 15, "brown_dk")
        px(img, 1, 0, "gold")
        wave = [0, 1, 0, -1][i]
        for x in range(2, 8):
            dy = round(math.sin((x + i * 1.5) * 0.9) * 0.6) if x > 3 else 0
            top = 1 + dy + (wave if x > 5 else 0)
            vline(img, x, top, top + 4 - (x - 2) // 3, "red")
            px(img, x, top, "orange")
        frames.append(img)
    return frames


@procedural("banner")
def _banner(spec: Spec):
    frames = []
    for i in range(spec.frames):
        img = new(spec.w, spec.h)
        hline(img, 1, 14, 1, "brown_dk")
        px(img, 0, 1, "gold")
        px(img, 15, 1, "gold")
        sway = [0, 1, 0, -1][i]
        poly(img, [(3, 2), (12, 2), (12 + sway, 22), (8 + sway, 28), (4 + sway, 22)], "red", outline="red_dk")
        rect(img, 4, 3, 11, 4, "gold")
        rect(img, 6 + sway // 2, 10, 9 + sway // 2, 13, "gold")
        px(img, 7 + sway // 2, 15, "gold")
        frames.append(img)
    return frames


@procedural("monument")
def _monument(spec: Spec):
    frames = []
    # obelisk
    img = new(spec.w, spec.h)
    rect(img, 3, 19, 12, 22, "stone", outline="black")
    rect(img, 6, 4, 9, 18, "stone_lt", outline="black")
    poly(img, [(6, 4), (9, 4), (8, 1), (7, 1)], "gold", outline="black")
    vline(img, 7, 6, 16, "stone")
    frames.append(img)
    # statue
    img = new(spec.w, spec.h)
    rect(img, 3, 18, 12, 22, "stone", outline="black")
    rect(img, 6, 7, 9, 17, "stone_lt", outline="black")
    rect(img, 6, 3, 9, 6, "stone_lt", outline="black")
    vline(img, 7, 9, 17, "stone")
    px(img, 8, 4, "black")
    vline(img, 11, 8, 16, "silver")
    frames.append(img)
    # well
    img = new(spec.w, spec.h)
    rect(img, 3, 14, 12, 22, "stone", outline="black")
    ellipse(img, 4, 13, 11, 15, "black")
    vline(img, 3, 6, 13, "brown")
    vline(img, 12, 6, 13, "brown")
    poly(img, [(1, 7), (14, 7), (8, 2)], "brown_lt", outline="brown_dk")
    rect(img, 7, 9, 8, 11, "tan", outline="brown_dk")
    frames.append(img)
    return frames


@procedural("cloud")
def _cloud(spec: Spec):
    frames = []
    shapes = [
        [(2, 8, 22, 18), (12, 2, 34, 18), (26, 7, 46, 18)],
        [(1, 10, 18, 18), (10, 4, 30, 18), (24, 9, 40, 18)],
        [(6, 9, 26, 18), (18, 3, 42, 18), (32, 10, 47, 18)],
    ]
    for v in range(spec.frames):
        img = new(spec.w, spec.h)
        for (x0, y0, x1, y1) in shapes[v]:
            ellipse(img, x0, y0, x1, y1, "white")
        arr = np.array(img)
        a = arr[:, :, 3] > 0
        for (x0, y0, x1, y1) in shapes[v]:
            ellipse(img, x0, y1 - 4, x1, y1, "silver")
        arr2 = np.array(img)
        arr2[~a] = 0
        frames.append(outline_alpha(Image.fromarray(arr2, "RGBA"), "silver"))
    return frames


@procedural("windmill")
def _windmill(spec: Spec):
    frames = []
    for i in range(spec.frames):
        img = new(spec.w, spec.h)
        # body
        poly(img, [(8, 46), (23, 46), (20, 18), (11, 18)], "stone_lt", outline="black")
        poly(img, [(9, 18), (22, 18), (16, 10)], "tile_red", outline="black")
        rect(img, 14, 38, 17, 46, "brown_dk", outline="black")
        rect(img, 14, 26, 17, 29, "blue_pale", outline="black")
        for yy in range(21, 44, 4):
            px(img, 12 + (yy // 4 % 2) * 3, yy, "stone")
        # blades (4 blades, rotate 22.5 deg per frame)
        cx, cy = 16, 14
        ang0 = i * (math.pi / 8)
        for b in range(4):
            a = ang0 + b * math.pi / 2
            ex, ey = cx + round(math.cos(a) * 13), cy + round(math.sin(a) * 13)
            line(img, cx, cy, ex, ey, "brown_dk")
            # sail: offset parallel line
            nx, ny = round(-math.sin(a) * 2), round(math.cos(a) * 2)
            mx, my = cx + round(math.cos(a) * 4), cy + round(math.sin(a) * 4)
            poly(img, [(mx, my), (ex, ey), (ex + nx, ey + ny), (mx + nx, my + ny)], "cream", outline="brown_dk")
        rect(img, cx - 1, cy - 1, cx + 1, cy + 1, "brown", outline="black")
        frames.append(img)
    return frames


@procedural("smoke")
def _smoke(spec: Spec):
    frames = []
    for i in range(spec.frames):
        img = new(spec.w, spec.h)
        r = 1 + i // 2
        y = 6 - i * 2 + r
        col = ["silver", "silver", "white", "white"][i]
        ellipse(img, 3 - r, y - r, 3 + r, y + r, col)
        if i >= 2:
            px(img, 3, y, "stone_lt")
        frames.append(img)
    return frames


# --------------------------------------------------------------------------------------
# Procedural sprites: interior / UI
# --------------------------------------------------------------------------------------
@procedural("hall_bg")
def _hall_bg(spec: Spec):
    img = new(spec.w, spec.h)
    rect(img, 0, 0, 479, 269, "stone_dk")
    for yy in range(0, 170, 8):
        for xx in range((yy // 8 % 2) * 8, 480, 16):
            rect(img, xx, yy, xx + 15, yy + 7, "stone", outline="stone_dk")
    rect(img, 0, 170, 479, 269, "slate")
    for yy in range(170, 270, 10):
        for xx in range((yy // 10 % 2) * 10, 480, 20):
            rect(img, xx, yy, xx + 19, yy + 9, "grey", outline="slate")
    for wx in (60, 200, 380):
        rect(img, wx, 30, wx + 30, 120, "blue_pale", outline="black")
        ellipse(img, wx, 16, wx + 30, 44, "blue_pale", outline="black")
        vline(img, wx + 15, 20, 120, "stone_dk")
    rect(img, 200, 130, 280, 269, "red", outline="red_dk")
    vline(img, 204, 130, 269, "gold_dk")
    vline(img, 276, 130, 269, "gold_dk")
    rect(img, 180, 140, 300, 160, "stone_lt", outline="black")
    rect(img, 228, 110, 252, 150, "gold_dk", outline="black")
    rect(img, 232, 120, 248, 148, "red_dk")
    for tx in (20, 400):
        rect(img, tx, 170, tx + 60, 190, "brown_lt", outline="black")
        rect(img, tx, 195, tx + 60, 200, "brown", outline="black")
    return [img]


@procedural("torch")
def _torch(spec: Spec):
    frames = []
    for i in range(spec.frames):
        img = new(spec.w, spec.h)
        rect(img, 3, 8, 4, 15, "brown", outline="brown_dk")
        rect(img, 2, 7, 5, 8, "slate")
        h = [5, 6, 5, 7][i]
        lean = [0, 1, 0, -1][i]
        poly(img, [(1 + lean, 7), (6 + lean, 7), (4 + lean, 7 - h)], "flame", outline="orange")
        poly(img, [(2 + lean, 7), (5 + lean, 7), (4 + lean, 9 - h)], "gold")
        frames.append(img)
    return frames


@procedural("panel")
def _panel(spec: Spec):
    return [nine_slice_frame(spec.w, spec.h, "brown_dk", "brown", "gold_dk", "black", corner_gem="gold")]


@procedural("panel_light")
def _panel_light(spec: Spec):
    return [nine_slice_frame(spec.w, spec.h, "parchment", "cream", "tan", "brown_dk")]


@procedural("button")
def _button(spec: Spec):
    normal = nine_slice_frame(spec.w, spec.h, "brown", "brown_lt", "gold_dk", "black")
    hi = nine_slice_frame(spec.w, spec.h, "brown_lt", "tan", "gold", "black", corner_gem="gold")
    return [normal, hi]


@procedural("bar_frame")
def _bar_frame(spec: Spec):
    img = new(spec.w, spec.h)
    rect(img, 0, 0, spec.w - 1, spec.h - 1, "navy", outline="black")
    rect(img, 1, 1, spec.w - 2, spec.h - 2, "navy", outline="gold_dk")
    rect(img, 2, 2, spec.w - 3, spec.h - 3, "black")
    return [img]


@procedural("icon_scroll")
def _icon_scroll(spec: Spec):
    img = new(16, 16)
    rect(img, 3, 3, 12, 12, "parchment", outline="brown_dk")
    rect(img, 2, 2, 13, 4, "cream", outline="brown_dk")
    rect(img, 2, 11, 13, 13, "cream", outline="brown_dk")
    for yy in (6, 8, 10):
        hline(img, 5, 10, yy, "brown")
    return [img]


@procedural("icon_hammer")
def _icon_hammer(spec: Spec):
    img = new(16, 16)
    line(img, 4, 12, 11, 5, "brown")
    line(img, 5, 13, 12, 6, "brown_lt")
    rect(img, 8, 2, 13, 6, "slate", outline="black")
    rect(img, 9, 3, 12, 3, "grey")
    return [outline_alpha(img)]


@procedural("icon_trophy")
def _icon_trophy(spec: Spec):
    img = new(16, 16)
    rect(img, 4, 2, 11, 7, "gold", outline="gold_dk")
    ellipse(img, 4, 5, 11, 9, "gold", outline="gold_dk")
    px(img, 2, 3, "gold_dk")
    px(img, 2, 4, "gold_dk")
    px(img, 3, 5, "gold_dk")
    px(img, 13, 3, "gold_dk")
    px(img, 13, 4, "gold_dk")
    px(img, 12, 5, "gold_dk")
    rect(img, 7, 10, 8, 11, "gold_dk")
    rect(img, 5, 12, 10, 13, "brown", outline="brown_dk")
    px(img, 6, 3, "white")
    return [outline_alpha(img)]


@procedural("cursor_hand")
def _cursor_hand(spec: Spec):
    img = new(8, 8)
    rect(img, 3, 0, 4, 4, "cream")
    rect(img, 1, 3, 6, 6, "cream")
    px(img, 1, 3, "cream")
    rect(img, 2, 7, 5, 7, "cream")
    return [outline_alpha(img)]


@procedural("arrow_up")
def _arrow_up(spec: Spec):
    img = new(8, 8)
    poly(img, [(3, 1), (0, 4), (6, 4)], "gold")
    rect(img, 2, 5, 4, 6, "gold")
    return [outline_alpha(img)]


@procedural("arrow_down")
def _arrow_down(spec: Spec):
    img = _arrow_up(spec)[0].transpose(Image.FLIP_TOP_BOTTOM)
    return [img]


@procedural("crest")
def _crest(spec: Spec):
    img = new(32, 32)
    poly(img, [(6, 4), (25, 4), (25, 18), (16, 28), (6, 18)], "gold_dk", outline="black")
    poly(img, [(8, 6), (23, 6), (23, 17), (16, 25), (8, 17)], "red")
    poly(img, [(8, 14), (23, 14), (23, 17), (16, 25), (8, 17)], "blue")
    rect(img, 13, 8, 18, 12, "gold")
    px(img, 13, 7, "gold"); px(img, 15, 7, "gold"); px(img, 18, 7, "gold")
    rect(img, 14, 16, 17, 21, "cream")
    return [img]


# --------------------------------------------------------------------------------------
# Spec table (canonical names)
# --------------------------------------------------------------------------------------
def _build_specs():
    S = SPECS
    S["grass"] = Spec(32, 16, 3, (16, 8), 0)
    S["grass_flowers"] = Spec(32, 16, 1, (16, 8), 0)
    S["path"] = Spec(32, 16, 1, (16, 8), 0)
    S["field_crop"] = Spec(32, 16, 2, (16, 8), 0)
    S["water"] = Spec(32, 16, 4, (16, 8), 2)
    S["shore"] = Spec(32, 16, 4, (16, 8), 0)
    S["castle"] = Spec(128, 128, 1, (64, 112), 0, raw=Raw("castle.png", fit=(124, 116), bottom=124))
    S["castle_gate_open"] = Spec(128, 128, 1, (64, 112), 0,
                                 raw=Raw("castle_gate_open.png", same_scale_as="castle"))
    S["hut"] = Spec(32, 32, 2, (16, 28), 0, raw=Raw("hut.png", split=2, fit=(30, 30), bottom=31))
    S["workshop"] = Spec(48, 40, 1, (24, 34), 0, raw=Raw("workshop.png", fit=(46, 38), bottom=39))
    S["worker"] = Spec(16, 16, 4, (8, 16), 6)
    S["worker_b"] = Spec(16, 16, 4, (8, 16), 6)
    S["tree"] = Spec(24, 32, 3, (12, 30), 0, raw=Raw("tree.png", split=3, fit=(24, 30), bottom=31))
    S["pine"] = Spec(24, 40, 1, (12, 38), 0, raw=Raw("pine.png", fit=(22, 38), bottom=39))
    S["bush"] = Spec(16, 12, 1, (8, 12), 0)
    S["rock"] = Spec(16, 10, 1, (8, 10), 0)
    S["flag"] = Spec(8, 16, 4, (1, 16), 4)
    S["banner"] = Spec(16, 32, 4, (8, 32), 4)
    S["monument"] = Spec(16, 24, 3, (8, 22), 0, raw=Raw("monument.png", split=3, fit=(16, 22), bottom=23))
    S["cloud"] = Spec(48, 20, 3, (24, 10), 0)
    S["windmill"] = Spec(32, 48, 4, (16, 46), 3)
    S["smoke"] = Spec(8, 8, 4, (4, 8), 3)
    S["hall_bg"] = Spec(480, 270, 1, (0, 0), 0, raw=Raw("hall_bg.png", stretch=True, crop=(0.0, 0.06, 1.0, 0.9)))
    S["torch"] = Spec(8, 16, 4, (4, 16), 6)
    S["panel"] = Spec(24, 24, 1, (0, 0), 0)
    S["panel_light"] = Spec(24, 24, 1, (0, 0), 0)
    S["button"] = Spec(24, 24, 2, (0, 0), 0)
    S["bar_frame"] = Spec(12, 12, 1, (0, 0), 0)
    S["icon_scroll"] = Spec(16, 16, 1, (0, 0), 0)
    S["icon_hammer"] = Spec(16, 16, 1, (0, 0), 0)
    S["icon_trophy"] = Spec(16, 16, 1, (0, 0), 0)
    S["cursor_hand"] = Spec(8, 8, 1, (0, 0), 0)
    S["arrow_up"] = Spec(8, 8, 1, (0, 0), 0)
    S["arrow_down"] = Spec(8, 8, 1, (0, 0), 0)
    S["crest"] = Spec(32, 32, 1, (16, 16), 0, raw=Raw("crest.png", fit=(32, 32), bottom=32))
    for name, spec in S.items():
        spec.proc = PROC.get(name)


_build_specs()

# --------------------------------------------------------------------------------------
# Raw-image pipeline
# --------------------------------------------------------------------------------------
MAGENTA = np.array([255, 0, 255], dtype=np.int32)


def chroma_mask(rgb: np.ndarray, tol: int = 110) -> np.ndarray:
    """True where a pixel is background (magenta-ish and connected to the border)."""
    d = np.sqrt(((rgb.astype(np.int32) - MAGENTA) ** 2).sum(-1))
    candidate = d < tol
    # magenta "spill" on anti-aliased edges: pinkish pixels
    r, g, b = rgb[..., 0].astype(int), rgb[..., 1].astype(int), rgb[..., 2].astype(int)
    candidate |= (r > 140) & (b > 140) & (g < np.minimum(r, b) - 70)
    # flood fill from the border: keep only background components touching an edge
    labels, _ = ndimage.label(candidate)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border = border[border != 0]
    return np.isin(labels, border)


def load_raw(raw: Raw) -> tuple[np.ndarray, np.ndarray]:
    """Return (palette index image, alpha bool) for a keyed raw source."""
    path = RAW_DIR / raw.file
    img = Image.open(path).convert("RGB")
    if raw.crop:
        l, t, r, b = raw.crop
        img = img.crop((int(l * img.width), int(t * img.height), int(r * img.width), int(b * img.height)))
    rgb = np.array(img)
    if raw.stretch:
        alpha = np.ones(rgb.shape[:2], dtype=bool)
    else:
        alpha = ~chroma_mask(rgb)
    idx = quantize_rgb(rgb)
    return idx, alpha


def bbox(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(alpha)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def split_columns(alpha: np.ndarray, n: int) -> list[tuple[int, int]]:
    """Split a sheet into n content columns separated by fully transparent gaps."""
    col = alpha.any(0)
    runs = []
    x = 0
    while x < len(col):
        if col[x]:
            x0 = x
            while x < len(col) and col[x]:
                x += 1
            runs.append((x0, x))
        else:
            x += 1
    # merge tiny runs into neighbours until n remain
    while len(runs) > n:
        gaps = [(runs[i + 1][0] - runs[i][1], i) for i in range(len(runs) - 1)]
        _, i = min(gaps)
        runs[i:i + 2] = [(runs[i][0], runs[i + 1][1])]
    if len(runs) != n:
        raise ValueError(f"expected {n} columns, found {len(runs)}")
    return runs


def block_mode_resize(idx: np.ndarray, alpha: np.ndarray, tw: int, th: int) -> tuple[np.ndarray, np.ndarray]:
    """Downsample by majority vote per destination pixel (colour and alpha)."""
    H, W = alpha.shape
    P = PAL_ARRAY.shape[0]
    ys = (np.arange(H) * th // H)
    xs = (np.arange(W) * tw // W)
    cell = (ys[:, None] * tw + xs[None, :])
    tot = np.bincount(cell.ravel(), minlength=tw * th)
    opaque = np.bincount(cell.ravel(), weights=alpha.ravel().astype(float), minlength=tw * th)
    out_alpha = (opaque > tot * 0.5).reshape(th, tw)
    key = cell[alpha] * P + idx[alpha]
    counts = np.bincount(key, minlength=tw * th * P).reshape(th, tw, P)
    out_idx = counts.argmax(-1)
    return out_idx, out_alpha


def compose(idx: np.ndarray, alpha: np.ndarray) -> Image.Image:
    h, w = alpha.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., :3] = PAL_ARRAY[idx]
    out[..., 3] = np.where(alpha, 255, 0)
    return Image.fromarray(out, "RGBA")


@dataclass
class Placement:
    sx: int  # source crop
    sy: int
    sw: int
    sh: int
    tw: int  # target content size
    th: int
    ox: int  # target offset
    oy: int


PLACEMENTS: dict[str, Placement] = {}


def place_from_raw(name: str, spec: Spec, raw: Raw) -> list[Image.Image]:
    idx, alpha = load_raw(raw)
    frames = []
    if raw.stretch:
        oi, oa = block_mode_resize(idx, alpha, spec.w, spec.h)
        return [compose(oi, oa)]
    columns = split_columns(alpha, raw.split) if raw.split > 1 else [(0, alpha.shape[1])]
    fit_w, fit_h = raw.fit or (spec.w, spec.h)
    bottom = raw.bottom if raw.bottom is not None else spec.h
    for fi, (cx0, cx1) in enumerate(columns):
        a_col = alpha[:, cx0:cx1]
        i_col = idx[:, cx0:cx1]
        if raw.same_scale_as:
            pl = PLACEMENTS[raw.same_scale_as]
        else:
            x0, y0, x1, y1 = bbox(a_col)
            sw, sh = x1 - x0, y1 - y0
            scale = min(fit_w / sw, fit_h / sh)
            tw, th = max(1, round(sw * scale)), max(1, round(sh * scale))
            ox = (spec.w - tw) // 2
            oy = (spec.h // 2 - th // 2) if raw.center_y else (bottom - th)
            pl = Placement(x0, y0, sw, sh, tw, th, ox, oy)
            if fi == 0:
                PLACEMENTS[name] = pl
        sub_i = i_col[pl.sy:pl.sy + pl.sh, pl.sx:pl.sx + pl.sw]
        sub_a = a_col[pl.sy:pl.sy + pl.sh, pl.sx:pl.sx + pl.sw]
        oi, oa = block_mode_resize(sub_i, sub_a, pl.tw, pl.th)
        frame = new(spec.w, spec.h)
        frame.paste(compose(oi, oa), (pl.ox, pl.oy))
        frames.append(frame)
    return frames


# --------------------------------------------------------------------------------------
# Post-processing hooks
# --------------------------------------------------------------------------------------
def snap_to_palette(img: Image.Image) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    alpha = arr[..., 3] >= 128
    idx = quantize_rgb(arr[..., :3])
    return compose(idx, alpha)


def post_gate_open(castle: Image.Image, gate_open: Image.Image) -> Image.Image:
    """Force castle_gate_open == castle everywhere except the gate window."""
    a = np.array(castle).copy()
    b = np.array(gate_open)
    h, w = a.shape[:2]
    # gate region: bottom centre
    gx0, gx1 = w // 2 - 16, w // 2 + 16
    gy0, gy1 = int(h * 0.60), h
    a[gy0:gy1, gx0:gx1] = b[gy0:gy1, gx0:gx1]
    return Image.fromarray(a, "RGBA")


# --------------------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------------------
def build_sprite(name: str, spec: Spec, force_procedural: bool, built: dict[str, list[Image.Image]]) -> list[Image.Image]:
    frames: list[Image.Image] | None = None
    if spec.raw is not None and not force_procedural and (RAW_DIR / spec.raw.file).is_file():
        try:
            frames = place_from_raw(name, spec, spec.raw)
        except (ValueError, KeyError, OSError) as exc:  # fall back to the procedural drawer
            print(f"  ! raw pipeline failed for {name}: {exc}; using procedural")
            frames = None
    if frames is None:
        if spec.proc is None:
            raise RuntimeError(f"no raw source or procedural drawer for {name}")
        frames = spec.proc(spec)
    frames = [snap_to_palette(f) for f in frames]
    if name == "castle_gate_open" and "castle" in built:
        frames = [post_gate_open(built["castle"][0], frames[0])]
    for f in frames:
        assert f.size == (spec.w, spec.h), f"{name}: frame size {f.size} != {(spec.w, spec.h)}"
    assert len(frames) == spec.frames, f"{name}: {len(frames)} frames != {spec.frames}"
    return frames


def write_strip(name: str, frames: list[Image.Image]) -> Path:
    w, h = frames[0].size
    strip = new(w * len(frames), h)
    for i, f in enumerate(frames):
        strip.paste(f, (i * w, 0))
    out = ASSET_DIR / f"{name}.png"
    strip.save(out, optimize=True)
    return out


def load_manifest() -> dict:
    path = ASSET_DIR / "manifest.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("sprites"), dict):
                return data
        except ValueError:
            pass
    return {"sprites": {}}


def write_manifest(manifest: dict):
    manifest["sprites"] = dict(sorted(manifest["sprites"].items()))
    (ASSET_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


def write_palette():
    (ASSET_DIR / "palette.json").write_text(
        json.dumps({"colors": list(PALETTE.values()), "names": list(PALETTE.keys())}, indent=1) + "\n",
        encoding="utf-8")


def build(names: list[str], force_procedural: bool) -> dict[str, list[Image.Image]]:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    built: dict[str, list[Image.Image]] = {}
    ordered = sorted(names, key=lambda n: (n != "castle", n))  # castle first (gate_open depends on it)
    if "castle_gate_open" in ordered and "castle" not in ordered and (ASSET_DIR / "castle.png").is_file():
        spec = SPECS["castle"]
        sheet = Image.open(ASSET_DIR / "castle.png").convert("RGBA")
        built["castle"] = [sheet.crop((0, 0, spec.w, spec.h))]
        if "castle" in SPECS and SPECS["castle"].raw and not force_procedural:
            # recompute placement so gate_open scales identically
            place_from_raw("castle", spec, SPECS["castle"].raw)
    for name in ordered:
        spec = SPECS[name]
        frames = build_sprite(name, spec, force_procedural, built)
        built[name] = frames
        out = write_strip(name, frames)
        ax, ay = spec.anchor_or_default()
        manifest["sprites"][name] = {"file": out.name, "w": spec.w, "h": spec.h, "frames": spec.frames,
                                     "anchor": [ax, ay], "fps": spec.fps}
        print(f"  {name:18s} {spec.w}x{spec.h} x{spec.frames}  -> {out.name}")
    write_manifest(manifest)
    write_palette()
    return built


# --------------------------------------------------------------------------------------
# Contact sheet
# --------------------------------------------------------------------------------------
def contact_sheet(out: Path, scale: int = 4):
    manifest = load_manifest()["sprites"]
    font = ImageFont.load_default()
    items = []
    for name, entry in manifest.items():
        sheet = Image.open(ASSET_DIR / entry["file"]).convert("RGBA")
        items.append((name, sheet))
    # grass field test tile (5x5 diamonds)
    grass = Image.open(ASSET_DIR / "grass.png").convert("RGBA")
    water = Image.open(ASSET_DIR / "water.png").convert("RGBA")
    field = new(32 * 6, 16 * 6)
    for j in range(5):
        for i in range(5):
            x = (i - j) * 16 + 80
            y = (i + j) * 8
            tile = grass.crop((((i * 3 + j) % 3) * 32, 0, ((i * 3 + j) % 3 + 1) * 32, 16))
            if (i, j) in ((3, 1), (4, 1), (4, 2)):
                tile = water.crop((0, 0, 32, 16))
            field.alpha_composite(tile, (x, y))
    items.append(("grass field 5x5", field))
    items.sort(key=lambda it: -it[1].height)
    pad = 8
    max_w = 1400
    x = pad
    y = pad
    row_h = 0
    positions = []
    for name, sheet in items:
        w, h = sheet.width * scale, sheet.height * scale
        if w > max_w - 2 * pad:
            s = max(1, (max_w - 2 * pad) // sheet.width)
            w, h = sheet.width * s, sheet.height * s
        if x + w > max_w:
            x = pad
            y += row_h + pad + 12
            row_h = 0
        positions.append((name, sheet, x, y, w, h))
        x += max(w, 6 * len(name) + 2) + pad
        row_h = max(row_h, h)
    total_h = y + row_h + pad + 12
    canvas = Image.new("RGBA", (max_w, total_h), (52, 64, 80, 255))
    draw = ImageDraw.Draw(canvas)
    for name, sheet, x, y, w, h in positions:
        s = w // sheet.width
        big = sheet.resize((sheet.width * s, sheet.height * s), Image.NEAREST)
        # checker under sprite to show transparency
        for cy in range(0, big.height, 8):
            for cx in range(0, big.width, 8):
                col = (70, 82, 98, 255) if (cx // 8 + cy // 8) % 2 else (60, 72, 88, 255)
                draw.rectangle([x + cx, y + cy, x + cx + 7, y + cy + 7], fill=col)
        canvas.alpha_composite(big, (x, y))
        draw.text((x, y + h + 1), name, fill=(238, 240, 244, 255), font=font)
    canvas.save(out)
    print(f"contact sheet -> {out}")


# --------------------------------------------------------------------------------------
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="build every sprite")
    parser.add_argument("--only", help="comma-separated sprite names")
    parser.add_argument("--procedural", action="store_true", help="ignore raw sources; use hand-coded drawers")
    parser.add_argument("--contact-sheet", type=Path, help="write a tiled 4x preview of all sprites")
    parser.add_argument("--list", action="store_true", help="list canonical sprite names")
    args = parser.parse_args(argv)
    if args.list:
        for name, spec in SPECS.items():
            src = "raw+proc" if spec.raw and spec.proc else ("raw" if spec.raw else "proc")
            print(f"{name:18s} {spec.w}x{spec.h} frames={spec.frames} fps={spec.fps} anchor={spec.anchor_or_default()} [{src}]")
        return
    names: list[str] = []
    if args.all:
        names = list(SPECS)
    elif args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        unknown = [n for n in names if n not in SPECS]
        if unknown:
            parser.error(f"unknown sprites: {', '.join(unknown)}")
    if names:
        build(names, args.procedural)
    if args.contact_sheet:
        contact_sheet(args.contact_sheet)
    if not names and not args.contact_sheet:
        parser.print_help()


if __name__ == "__main__":
    main()
