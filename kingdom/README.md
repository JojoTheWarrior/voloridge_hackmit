# Kingdom

A calm 8-bit pixel-art dashboard for WarSignal missions. A fortress sits on an
isometric island; every active mission raises a worker hut, every finished
mission adds a monument (or a flag for failed runs). Click the castle to walk
into the great hall and browse missions.

```bash
python main.py kingdom                 # windowed, 3x integer upscale of 480x270
python main.py kingdom --scale 2
python main.py kingdom --scene completed
python main.py kingdom --screenshot out.png --frames 120   # headless render
```

| Flag | Meaning |
| --- | --- |
| `--scale N` | Integer upscale factor (window is resizable; the canvas stays crisp) |
| `--scene field\|castle\|current\|queue\|completed` | Start scene |
| `--screenshot PATH` | Run headless (`SDL_VIDEODRIVER=dummy`) and save the last frame |
| `--frames N` | Stop after N frames (default 120 when headless) |
| `--root PATH` | Repo root containing `missions/` (default: this repo) |

Audio is always disabled (`SDL_AUDIODRIVER=dummy`).

## Controls

| Input | Field | Castle |
| --- | --- | --- |
| Click castle / Enter | Enter the castle | Select |
| Esc / Backspace | — | Back / leave the castle |
| Arrows | Pan camera | Move selection / scroll |
| Mouse wheel | Zoom | Scroll lists |
| Home | Reset camera | — |
| Ctrl+Q | Quit | Quit |

## Data

`kingdom/data.py` is read-only and polls `missions/` every ~2 s:

- `queue.txt` → pending hypotheses
- `in_progress.txt` → active missions (elapsed from the file mtime, or a
  leading ISO timestamp when present)
- `runs/<YYYYMMDD>-<NNN>-<slug>/{manifest,stats,judge}.json`, `note.md`,
  `viz.png` and `runs/INDEX.md` → completed missions
- `failed.txt` → failures

Missing files and fields are tolerated everywhere.

## Layout

```
kingdom/
  app.py      480x270 canvas, integer upscale, scene stack, fades, CLI
  field.py    isometric island, castle, huts/workers, monuments, camera
  castle.py   great hall + menus (current / queue / completed)
  ui.py       9-slice panels, buttons, scroll lists, progress bars
  data.py     read-only mission adapter
  assets.py   sprite manifest loader (placeholders if a sprite is missing)
  text.py     crisp pixel text (assets/fonts/pixel.ttf)
  assets/     PNG strips, manifest.json, palette.json, fonts/
  tools/      make_assets.py – reproducible sprite pipeline
```

## Tests

```bash
pytest tests/test_kingdom_*.py -q
```
