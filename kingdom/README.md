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
| `--no-pull` | Disable the background `git pull` loop |
| `--pull-interval S` | Seconds between background pulls (default 60) |
| `--no-http` | Disable the GitHub HTTP poller |
| `--http-interval S` | Seconds between HTTP fetches (default 30) |
| `--remote owner/repo` | Repository fetched by the HTTP poller |
| `--branch NAME` | Branch fetched by the pollers (default `main`) |

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
- `status/<mission_id>.json` → live missions (see below)

Missing files and fields are tolerated everywhere.

## Live missions

GitHub `main` is the source of truth. Every running mission agent writes
`missions/status/<mission_id>.json` (see `missions/status/SCHEMA.md`) and
pushes it as it reaches new stages. A daemon thread runs
`git pull --rebase --autostash` every 60 s (`--pull-interval`) so the castle
stays fresh; disable it with `--no-pull`. A pull that finishes forces the
data adapter to refresh on the next frame.

What you see:

- **Current missions** cards show live status files first: the title, the
  stage (`QUEUED`/`PLANNING`/`STATS`/…), an agent tag (first 8 chars of the
  session id), the reported `progress` fraction and live `signal` colour,
  and the latest status `message`. Legacy `in_progress.txt` lines are still
  shown as a fallback (dropped when a status file carries the same
  hypothesis).
- **Queue** rows parse `R2 | R2-0017 | hypothesis` prefixes and show the
  round + parent mission id next to the hypothesis.
- **Completed missions** merge `done`/`failed` statuses into their run
  folders (actionability score, trade idea, agent url, round); statuses
  without a run folder synthesize a completed row. The stats line gains
  `A=<actionability>` and the detail view gains a compact TRADE block.
- The field HUD shows tiny `sync Ns`/`sync err` and `net ok`/`net err`
  indicators.

### HTTP poller

When `git pull` isn't possible (shallow checkout, no credentials) an HTTP
poller fetches the same files straight from GitHub: the contents API for
`missions/status/*.json` and `raw.githubusercontent.com` for `queue.txt`,
`in_progress.txt` and `failed.txt`. Results land in
`.kingdom_cache/missions/` and are overlaid on the local `missions/` dir —
the overlay wins for `status/` entries with an equal-or-later `updated_at`.
Set `GITHUB_TOKEN` to raise the anonymous API rate limit. Flags:
`--no-http`, `--http-interval`, `--remote`, `--branch`.

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
