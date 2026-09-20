# Kingdom web frontend — design

Date: 2026-09-20

## Goal

Replace the temporary Bloomberg-style `terminal/` UI with a minimalist, light,
YC-style web app in a new `web/` folder. This spec covers the frontend only,
running on hardcoded example data. The backend comes later.

Product idea the UI is shaped around: you link datasets, then assign missions
that agentically search for connections and insights between them.

## Visual direction

Chosen after surveying 22 Summer 2026 YC company sites: "white and grotesk"
(Billow, Hardware Intelligence, Experiential Labs).

- Background `#FFFFFF`; sidebar `#FAFAFA`.
- Ink `#0A0A0A`; muted text `#8C8C8C`; hairlines `#E5E5E5` / `#EFEFEF`;
  subtle fill `#F4F4F4`. No other colors. No gradients, no shadows.
- Type: Geist (400, 500 only) for everything; Geist Mono for numbers and stats.
  Headlines use tight negative tracking.
- Primary action is an ink-filled pill; everything else is outline or ghost.
  At most one filled button per view.
- Status is shape, not color: filled dot = running, hollow dot = done,
  hollow dot with a slash/x glyph = failed.
- Logo: a simple solid castle mark (crenellated silhouette with an arched
  door) as an inline SVG component, next to the lowercase wordmark `kingdom`.
  The same SVG is the favicon.
- Motion: only small, fast transitions (150ms fades, the running-step spinner).

## Layout

One app shell: persistent left sidebar (240px) + main area. On narrow screens
(<768px) the sidebar becomes a slide-over opened from a menu button.

Sidebar, top to bottom:

1. Castle logo + wordmark (links to home).
2. "New mission" outline button.
3. Mission list grouped "Running" then "Done" (failed missions sit in Done),
   each row a status dot + truncated title; the active mission is highlighted.
4. "Datasets" pinned at the bottom.

## Views

### New mission — `/`

Centered column. Headline "What should we look into?". Below it a composer:
multiline text input, a row of dataset chips (toggle which linked datasets the
mission may use; all on by default), and a round ink submit button. Enter
submits, Shift+Enter inserts a newline. Submitting an empty prompt does
nothing. Below the composer, three example missions; clicking one fills the
composer.

Submitting creates a mission in the in-memory store with status `running`,
navigates to its mission view, and the mock API advances it through its steps
on a timer so the full flow can be seen end to end.

### Mission — `/missions/:id`

Reads like a chat thread, max-width 720px:

1. The hypothesis as a right-aligned gray bubble.
2. Agent steps: plan → pull data → test → chart → write-up. While running,
   steps are expanded: finished steps muted with a check, the current step in
   ink with a spinner. When the mission is done the steps collapse into one
   "Worked for 4m 12s" line that expands on click.
3. Result card (done missions): two-series line chart (ink + gray), then a
   stat row — correlation, best lag, p-value, n — in Geist Mono, then the
   agent's note rendered as prose, then a one-line verdict.
4. Failed missions show the error message in place of the result card.

Unknown mission id → a small "Mission not found" state with a link home.

### Datasets — `/datasets`

Header "Datasets" + "Link dataset" ink pill. A hairline table: name, source
(external link), series count, date range, last synced. "Link dataset" opens a
small dialog with name and URL fields; submitting adds a row to the in-memory
store (URL is validated as http/https; name is required). Empty state is an
invitation with the same button.

## Architecture

`web/` — Vite + React + TypeScript + Tailwind CSS v4, React Router, Recharts.

```
web/
  index.html
  src/
    main.tsx            app entry, router
    index.css           Tailwind import + design tokens (@theme)
    types.ts            Mission, MissionStep, MissionResult, Dataset
    api/
      index.ts          the interface every component uses
      mock.ts           in-memory store + timers, seeded from fixtures
      fixtures.ts       example missions and datasets
    hooks/              useMissions, useMission, useDatasets
    components/
      AppShell, Sidebar, CastleLogo, StatusDot, Composer, DatasetChips,
      MissionThread, StepList, ResultCard, SeriesChart, StatRow,
      DatasetTable, LinkDatasetDialog
    pages/
      NewMissionPage, MissionPage, DatasetsPage
```

Boundary that matters: components only import from `api/index.ts` and the
hooks. `api/index.ts` exposes `listMissions`, `getMission`, `createMission`,
`listDatasets`, `linkDataset`, and `subscribe(listener)`; all async. When the
backend exists, `mock.ts` is swapped for an HTTP implementation and no
component changes.

Fixtures are modelled on real runs in `missions/runs/` (e.g. GDELT Iran events
vs Brent, Tehran wind vs PM2.5) so examples look like the real product:
roughly 2 running, 5 done, 1 failed mission; 4 datasets (GDELT, Yahoo Finance,
Open-Meteo weather, CAMS air quality).

## Removing the terminal

Delete `terminal/`, the `terminal` subcommand in `main.py`, and the Terminal
section and command-table row in `README.md`. Keep
`warsignal/mission/monitor.py` (the real-data state builder) — the future
backend will reuse it. `tests/test_terminal.py` is mostly monitor tests:
rename it to `tests/test_monitor.py`, keep every test that exercises
`monitor.py`, and delete only the tests that need `terminal.app` /
`terminal.snapshot` (the Flask routes, index HTML, and snapshot tests). Flask
stays in `requirements.txt` (`warsignal/ui` and `warsignal/graph` use it). Add
a short "Web" section to `README.md`
(`cd web && npm install && npm run dev`). `kingdom/` (pygame) is untouched.

## Testing

Vitest + React Testing Library, run with `npm test`; `npm run build` doubles
as the type-check gate.

- Mock API: create → running → steps advance → done (fake timers); subscribe
  notifies; linkDataset validation (empty name, non-http URL).
- Composer: Enter submits, Shift+Enter doesn't, empty prompt blocked, example
  click fills input, chip toggling changes the submitted dataset list.
- Sidebar: grouping by status, active highlight, failed in Done.
- Mission page: running shows expanded steps; done shows collapsed summary
  that expands; failed shows error; unknown id shows not-found.
- Datasets: table renders fixtures, dialog adds a row, validation errors shown,
  empty state.
- Python: full existing pytest suite still passes after the terminal removal.

Visual check in the browser preview at desktop and mobile widths before
calling it done.

## Out of scope

Backend, auth, real dataset ingestion, real agent execution, dark mode,
the marketing/landing page.
