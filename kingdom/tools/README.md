# Kingdom art pipeline

`kingdom/tools/make_assets.py` builds every sprite in `kingdom/assets/` from
two kinds of sources and writes `manifest.json` + `palette.json`:

* **Raw generated pictures** in `kingdom/tools/raw/` (AI-generated, ~1024 px,
  solid magenta `#FF00FF` background). Used for the buildings, trees, monuments,
  crest and the great-hall background.
* **Procedural drawers** (hand-coded pixel art in `make_assets.py`, one
  function per sprite decorated with `@procedural("name")`). Used for tiles,
  animations, UI 9-slices and icons, and as the offline fallback for every
  sprite that also has a raw source.

```bash
pip install -r requirements.txt                       # pillow, numpy, scipy
python -m kingdom.tools.make_assets --all             # rebuild everything
python -m kingdom.tools.make_assets --only castle,hut # a subset
python -m kingdom.tools.make_assets --all --procedural   # no raw sources, fully offline
python -m kingdom.tools.make_assets --all --contact-sheet /tmp/sheet.png  # 4x preview of all strips
python -m kingdom.tools.make_assets --list            # canonical names, sizes, frame counts
```

## What the raw pipeline does

1. Optional fractional crop (`Raw.crop`), then chroma-key: pixels within a
   tolerance of magenta (plus pinkish anti-alias spill) that are connected to the
   image border become transparent (`scipy.ndimage.label` flood fill).
2. Quantize every source pixel to the palette (nearest RGB).
3. Split multi-variant sheets into columns at fully transparent gaps
   (`Raw.split`), crop each to content.
4. Scale to fit the `Raw.fit` box preserving aspect, **block-mode voting**:
   each destination pixel takes the most common palette colour of its source
   block; alpha is the majority vote, so output alpha is strictly 0/255 and
   there is no anti-aliasing or dithering.
5. Bottom-centre the result at `Raw.bottom` inside the sprite frame so the
   manifest anchor lands on the building base.
6. `castle_gate_open` reuses the exact placement computed for `castle` and is
   then forced pixel-identical to `castle` outside the gate window
   (`post_gate_open`), so the two swap seamlessly.
7. `hall_bg` uses `stretch=True` (no keying, fills 480x270 after a crop that
   keeps the throne in frame).

## Regenerating a raw source

Prompt style that works (gpt-image class models):

> flat 8-bit pixel art sprite of ..., front three-quarter view like a mobile
> strategy game building, chunky visible pixels, limited 16 colour palette,
> calm low-saturation colours, dark 1 pixel outlines, NO anti-aliasing, NO
> gradients, NO dithering, flat colours only, centered, solid flat pure magenta
> (#FF00FF) background, no ground, no shadows, nothing else.

For variant sheets add "N variants side by side in a row, evenly spaced with
clear gaps of magenta between them" and set `Raw(split=N)`. Very small targets
(<= 24 px) come out cleaner when the prompt asks for "big simple shapes, low
detail". Keep raw files under ~2 MB (they are committed); if a source is
larger, downscale it first with nearest-neighbour.

If a generated sprite looks bad, delete/rename its raw file or run with
`--procedural` — the hand-coded drawer for that name is used instead.

## Conventions

* Strips are horizontal, frames left-to-right; `fps: 0` means frames are
  variants chosen by index, not animated.
* Ground tiles are 32x16 2:1 diamonds (`iso_mask`), 4 px wider per row, so
  tiles placed at `(±16, ±8)` offsets butt seamlessly. `shore` frames are edges
  0=N (top-left), 1=E (top-right), 2=S (bottom-right), 3=W (bottom-left).
* 9-slice frames (`panel`, `panel_light`, `button`, `bar_frame`) have 8 px
  corners/edges (4 px for `bar_frame`).
* Font: `kingdom/assets/fonts/pixel.ttf` is Press Start 2P (OFL, licence in
  `OFL.txt` next to it), rendered at 8 px by `kingdom/text.py`.
