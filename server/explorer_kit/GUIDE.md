# Building a Kingdom explorer

An explorer is a small static website you write for one mission. It is shown inside the mission page, in a sandboxed frame, next to the thread and the report.

## What it is for

Some findings are things, not statistics: buildings, clinics, parcels, ships, documents. A chart cannot show them. An explorer lets a person **see each one and poke at it**: pan to it, open it, read why it was flagged, look at the evidence, and know who could act.

- Every row is one specific, real thing someone could act on, with the evidence that put it there.
- Lead with the finding. The first screen should already show the answer: ranked, filtered to what matters.
- It is an instrument for the results you already have, not a second analysis. No new claims appear here.
- **Real data only.** Use only results produced in this session. Never ship the kit's `data.json` or any row of it, never invent or pad rows, never use placeholder images. The sample is synthetic, marked `"demo": true`, and shows a "Demo data" badge; your explorer has neither. If the results are thin, build a smaller explorer.

## What you are given

| File | What it is |
| --- | --- |
| `kit/kit.css` | Kingdom's design system: tokens for light and dark, fonts, and component classes (`k-…`). |
| `kit/kit.js` | Optional helpers on one global, `Kingdom`: theme sync, `loadData`, a MapLibre map with matching basemaps, scored-point and heatmap layers, `fmt.pct / num / date`, `el`, `state`, `evidence`, `rankedList`. Short; read it. |
| `index.html` + `data.json` | One complete worked example (likely asbestos-cement roofs on a map). Copy its structure, not its content. |

The kit is a starting point. Restructure the example or replace it entirely when the finding has another shape. What may not change is the look, and the rules below.

## Design rules (hard)

- Use only the kit's tokens (`var(--color-ink)`, `--color-muted`, `--color-line`, …). **No colours at all**: no red for risk, no green for good, no brand blues. Encode magnitude with ink opacity, size, position or order; never hue. Photographs and imagery are the only colour on the page.
- No shadows, gradients, glows, blurs or glass. Surfaces are flat paper with 1px hairlines; corners 6 to 12px, pills fully round.
- Type: Geist at weight 400 or 500 only, nothing bolder. Every number is in Geist Mono (`k-mono`, `k-stat`, `k-hero`). Headings use slightly tight tracking. UI text is 13px, labels 12px muted, prose 14px.
- Words: sentence case everywhere. No exclamation marks, no emoji, no hype. Labels say plainly what a thing is. Units and dates are explicit ("20 Sep 2026", "1,255 m²").
- At most one ink-filled button (`k-btn k-primary`) in a view, and often none. Everything else is an outline pill or a quiet row.
- Motion is 150ms fades only, and `prefers-reduced-motion` is respected (the kit does both).
- **Light and dark must both look right.** Never hard-code a colour, in CSS, SVG, canvas or map paint. In JavaScript read tokens with `Kingdom.theme.token('ink')` and repaint inside `Kingdom.theme.onChange(...)`.
- It must work at 375px wide. The kit's frame turns the side panel into a bottom sheet under 640px; keep anything you add inside that flow. The page itself never scrolls: panels do.
- Keyboard: every action is a real `<button>`, `<a>` or `<input>`; focus rings stay visible; the list is reachable without the map.
- Always design the empty, loading and error states (`Kingdom.state`). A filter that hides everything should say so and offer the way back.

## Technical rules (hard)

- Static files only. The entry point is `index.html`. No build step, no server, no frameworks that need one.
- Reference the kit **exactly** as `kit/kit.css` and `kit/kit.js`, relative. Load `kit.js` in `<head>`. Do not copy, inline, rename or edit the kit: Kingdom serves its own copy at that path and discards any `kit/` folder you ship. Put your own styles in a `<style>` block or your own CSS file.
- Load your data from relative files (`Kingdom.loadData('data.json')`). No absolute paths, no API calls for the findings themselves.
- Scripts and styles may come only from `unpkg.com`, `cdn.jsdelivr.net` and `fonts.googleapis.com` (a content security policy enforces this). Pin versions. Images and map tiles may come from anywhere over https. No `eval`, no workers from remote URLs.
- The frame is sandboxed with an **opaque origin**: no `localStorage`, `sessionStorage`, cookies, IndexedDB or service workers (they throw), and nothing that assumes `allow-same-origin`. Keep state in memory and, if it is worth keeping, in the URL hash. No forms that submit, no `alert`/`confirm`, no top-level navigation.
- Every external link opens a new tab (`target="_blank" rel="noopener"`); `kit.js` also enforces this for you.
- Put text into the page with `Kingdom.el(...)` or `textContent`. Never build HTML strings from data.
- For maps use `Kingdom.map`. It loads MapLibre GL 5 (version 4 draws nothing inside a sandboxed frame), a basemap drawn from the kit's tokens on OpenFreeMap tiles, and Esri satellite imagery; all keyless. `map.gl` is the raw MapLibre map if you need more. Keep the attribution control.
- Keep it modest: aim for under 5 MB in total and under about 5,000 rows or features in the browser; the archive limit is 200 files and 40 MB. Downsample or aggregate huge datasets and say in the description that you did. Resize images (around 800px wide, JPEG or WebP). **Precompute in your session, not in the browser**: ship scores, ranks, bins and joins ready to draw.
- Allowed file types: `html css js mjs json geojson csv txt png jpg jpeg webp gif svg woff2`.

## Adapting the example to other shapes of finding

Keep the frame (quiet header, stage, side panel with a detail view and a ranked list) and change the stage.

- **Change over time.** Add a time slider (`k-range`) or a segmented toggle of periods that filters the same marks; show the selected date in mono beside it. Precompute one value per period per item; the detail panel gets a small two-tone line chart in ink and gray.
- **Before and after.** Two evidence frames side by side with dated captions, or one frame with a draggable vertical divider revealing the second image. Same crop, same scale, dates in the captions.
- **Image-first evidence.** Replace the map with a gallery grid of `k-evidence` tiles sorted by score, each with a mono score and a one-line caption; clicking a tile opens the same detail panel. Lazy-load images.
- **When geography is not the point.** Make the stage a sortable, filterable table: hairline rows, right-aligned mono numbers, sort on header click, a text filter, the same threshold slider, and the detail panel on row click. No map just because there are coordinates.
- **Small multiples.** A grid of identical tiny charts or maps, one per group, sharing one scale and one legend, ordered by the finding; clicking one makes it the detail.
- **Networks or flows.** Prefer a ranked list of the strongest links with a detail view over a hairball. Draw a graph only if its structure is the finding.

## Before you deliver

1. Open it with `?theme=light` and `?theme=dark`. Both look designed; nothing is invisible, nothing is coloured.
2. Narrow the window to 375px. Nothing overflows sideways; the panel is a usable bottom sheet.
3. The console is clean: no errors, no CSP violations, no failed requests.
4. Use it with the keyboard only. Select something, clear it, change every control.
5. Push every filter to its extreme and pan away from the data: the empty states appear and lead back.
6. Every row is real and traceable to this session's results. No sample data, no invented rows, no placeholder images, no "Demo data" badge.
7. Paths are relative, the kit is referenced as `kit/kit.css` and `kit/kit.js`, and the archive contains `index.html` at its root.
8. Title and description are plain sentences that say what is on the page.
