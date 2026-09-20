# Preparation verification

Checked 2026-09-20.

- Dedicated `kingdom-video:local` container image built successfully.
- Ruff passed for the renderer, assembler and inert mission-draft preparer.
- Preview rendered in a container with networking disabled: 1920×1080,
  30 fps, 900 frames, 30.000 seconds, H.264/yuv420p and stereo AAC audio.
- Both generated keyframes and 15 samples decoded from the encoded MP4 were
  visually inspected. Text tracking, camera crops, cursor positions, actual
  dataset navigation and actual view-toggle transitions are visible.
- Audio decode/volume check passed: mean -35 dBFS, peak -15 dBFS, no clipping.
  Sound design is an intentionally quiet synthesized bed with typing/click
  accents. No narration is recorded yet; listening review remains for final mix.
- The exact 120-second timeline has no gaps or overlaps.
- Final readiness checks correctly identify missing research footage and reject
  final rendering. The final assembler was linted and its missing-input path
  checked; assembly with completed mission clips remains pending.
- Captures used only the existing homepage and dataset library. An illustrative
  question was typed but never submitted. Keyboard clearing restored the empty
  composer with Start mission disabled. Dataset card view was restored.
- No Devin messages, mission submissions, report/explorer generation requests,
  uploads, publication, host package installs or application-source edits.

The application is being edited concurrently. Captures are suitable for the
style study, and final shots must be refreshed against the finished UI.

Logo refinement: the React mark and favicon share identical 32-unit vector
geometry. Browser preview checked both light/dark backgrounds, 16–48px sizes and
the actual app header. Video vector rasterization checked in a rendered 1080p
closing frame. Web production build, lint, the two existing CastleLogo tests,
and video Ruff passed. No new research or complete video rerender was needed.
