# Kingdom video production

The target is a fully produced **120-second 1920×1080, 30 fps MP4**. This folder
prepares motion graphics, shot timing, capture provenance and local rendering.
It does not run Devin. See [STORYBOARD.md](STORYBOARD.md) for the full edit plan.

## Ready now

- `output/kingdom-style-preview.mp4`: 30-second motion study using actual UI
  screenshots. White typography, horizontal tracking, camera zoom/pan, animated
  cursor, actual dataset-navigation/view-toggle transitions, and click pulses.
- `output/contact-sheet.jpg`: twelve sampled frames for visual review.
- `output/verification.json`: encoded-media metadata and SHA-256 fingerprint.
- `edit.json`: an exact 120-second scene plan with empty research-media slots.
- `render.py`: deterministic Pillow/FFmpeg motion renderer; no network calls.
- `assemble.py`: local scene assembly, optional narration/music mix, and final
  duration/frame-count verification. It rejects missing or too-short clips.
- `assets/capture-manifest.json`: screenshot provenance and real click targets.
- `assets/fonts/`: Kingdom's existing Geist/Geist Mono with their font licenses.

The illustrative prompt was typed but never submitted and was cleared after
capture. The dataset view was restored. Original screenshots are retained;
camera crops and cursor choreography are editorial. Research scenes await the
missions Tom runs himself. The preview uses synthesized original audio, no
downloaded music and no narration.

## Refined castle

The app component and `web/public/castle.svg` now use a symmetric 32-unit mark
with equal battlements, subtle corner radii and a smooth arch. The video renderer
reads this vector and uses supersampled curves instead of its former polygon.
It reads the app asset when available, or the bundled `assets/castle.svg` copy
when running in the isolated video container. Refresh that copy before rendering:

```sh
cp web/public/castle.svg demo-video/assets/castle.svg
```

`logo-preview.html` shows both backgrounds, before/after, and small-size use.
`output/kingdom-logo-refined.png` is its captured preview;
`output/logo-video-frame.png` verifies the updated large video mark. The original
30-second MP4 remains the original style study; the final film will use the new
mark and faster pacing around real mission results.

## Container workflow

From the application repository:

```sh
docker build -t kingdom-video:local demo-video
docker run --rm --network none --cpus 4 \
  -v "$PWD/demo-video:/film" kingdom-video:local python render.py --preview
docker run --rm --network none \
  -v "$PWD/demo-video:/film" kingdom-video:local python render.py --stills
docker run --rm --network none \
  -v "$PWD/demo-video:/film" kingdom-video:local ruff check .
docker run --rm --network none \
  -v "$PWD/demo-video:/film" kingdom-video:local python render.py --final-check
```

`--final-check` intentionally exits nonzero until real required footage is
assigned. It cannot create a plausible-looking final film with empty results.
Use `--preflight` for a successful readiness report that lists pending scenes.
Container package installs never modify host tools or the application stack.
The renderer reads mounted local assets and writes only to this folder.

## Final assembly once scene clips exist

Set each scene's `asset` in `edit.json` to its local rendered video, relative to
this folder. `in_seconds` may optionally specify where to start within that clip.
Clips must already contain their transitions, captions and sound-independent
motion; the assembler preserves their order and normalizes dimensions/frame rate.
It never stretches research footage or repeats a clip to cover a missing scene.
All eight clips must exist, including the opener, closing and either supporting
missions or the extended hero sequence occupying the breadth slot.

```sh
docker run --rm --network none -v "$PWD/demo-video:/film" kingdom-video:local \
  python assemble.py
docker run --rm --network none -v "$PWD/demo-video:/film" kingdom-video:local \
  python assemble.py --render --narration assets/narration.wav --music assets/final-mix.wav
```

Audio tracks are optional. Original clip audio is intentionally excluded to
avoid overlapping desktop sounds; a final-mix file can contain the intended
music and click accents. Narration remains at unity gain and music is attenuated.
Review the actual mix before delivery. Final outputs are `kingdom-demo.mp4` and
`final-verification.json`.

Assets and renders are ignored by Git. Keep this folder on the workstation or
explicitly package it for handoff; a code-only clone will need the same captures
and existing application fonts. Re-capture final footage after UI changes.

`prepare_missions.py` and the ignored request JSONs are unsubmitted drafts from
before Tom clarified that he will run the missions. They have no submission
code and are not part of video production. Do not submit them.
