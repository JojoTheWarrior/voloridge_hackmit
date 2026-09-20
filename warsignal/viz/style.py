"""Shared visual standard for every WarSignal pygame surface (mission viz + graph reels).

Fonts are bundled under warsignal/viz/fonts (Inter + JetBrains Mono, both OFL) so
every machine renders identical output. The verdict scale maps the judge scores
onto a five-step NOISE -> STRONG SIGNAL ladder that is shown in the banner.
"""

from __future__ import annotations

from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "fonts"

FONT_FILES = {
    "regular": "Inter-Regular.ttf",
    "italic": "Inter-Italic.ttf",
    "semibold": "Inter-SemiBold.ttf",
    "bold": "Inter-Bold.ttf",
    "bolditalic": "Inter-BoldItalic.ttf",
    "black": "Inter-ExtraBold.ttf",
    "mono": "JetBrainsMono-Regular.ttf",
    "monobold": "JetBrainsMono-Bold.ttf",
    "monoitalic": "JetBrainsMono-Italic.ttf",
}

PALETTE = {
    "bg": (13, 15, 20),
    "panel": (18, 21, 28),
    "grid": (38, 43, 54),
    "axis": (70, 78, 94),
    "text": (236, 240, 246),
    "muted": (140, 152, 172),
    "faint": (92, 102, 120),
    "accent": (76, 201, 240),
    "war": (247, 37, 133),
    "ceasefire": (6, 214, 160),
    "series": [(76, 201, 240), (247, 37, 133), (255, 209, 102), (6, 214, 160), (181, 126, 255)],
}

# (label, colour) indexed by tier 0..4
VERDICT_TIERS = [
    ("NOISE", (120, 130, 150)),
    ("WEAK", (255, 159, 67)),
    ("MODERATE", (255, 209, 102)),
    ("SIGNAL", (6, 214, 160)),
    ("STRONG SIGNAL", (76, 201, 240)),
]
VERDICT_FAILED = ("FAILED", (247, 37, 133))

# Spacing constants; every text block must respect these so nothing overlaps.
PAD = 16
GAP = 8
LINE_GAP = 4


def load_fonts(pygame):
    """Return {role: pygame.font.Font} using bundled TTFs, falling back to DejaVu."""
    fonts = {}
    sizes = {
        "verdict": ("black", 26),
        "title": ("bold", 21),
        "subtitle": ("italic", 13),
        "h": ("bold", 14),
        "hi": ("bolditalic", 12),
        "body": ("regular", 13),
        "small": ("regular", 11),
        "mono": ("mono", 12),
        "monobold": ("monobold", 13),
        "monosmall": ("mono", 10),
        "brand": ("black", 20),
    }
    for role, (face, size) in sizes.items():
        path = FONT_DIR / FONT_FILES[face]
        if path.exists():
            fonts[role] = pygame.font.Font(str(path), size)
        else:
            fonts[role] = pygame.font.SysFont("dejavusans", size, bold="bold" in face or face == "black",
                                              italic="italic" in face)
    return fonts


def verdict_tier(result) -> tuple[int, str, tuple[int, int, int]]:
    """Map a mission result dict to (tier, label, colour).

    Tier is driven by the judge validity score (0-10) and softened by the
    supported probability and permutation p; failed runs are tier -1.
    """
    if str(result.get("status", "")).lower() in ("failed", "error"):
        return -1, *VERDICT_FAILED
    scores = result.get("scores") or {}
    validity = scores.get("validity", result.get("validity"))
    supported = scores.get("supported_prob", result.get("supported_prob"))
    stats = result.get("stats") or {}
    perm = stats.get("perm_p", result.get("perm_p"))
    try:
        validity = float(validity) if validity is not None else 0.0
    except (TypeError, ValueError):
        validity = 0.0
    score = validity
    if supported is not None:
        try:
            score = 0.7 * validity + 3.0 * float(supported)
        except (TypeError, ValueError):
            pass
    if perm is not None:
        try:
            perm = float(perm)
            if perm > 0.2:
                score = min(score, 3.9)
            elif perm > 0.05:
                score = min(score, 5.9)
        except (TypeError, ValueError):
            pass
    if score < 2.0:
        tier = 0
    elif score < 4.0:
        tier = 1
    elif score < 6.0:
        tier = 2
    elif score < 8.0:
        tier = 3
    else:
        tier = 4
    label, color = VERDICT_TIERS[tier]
    return tier, label, color
