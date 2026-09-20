# Kingdom Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `terminal/` with a minimalist white-and-grotesk React app in `web/` that runs the full new-mission → mission-thread → datasets flow on mock data.

**Architecture:** Vite single-page app. Components talk only to an `Api` interface obtained from React context; the only implementation today is an in-memory mock seeded from fixtures that advances running missions on a timer. Swapping in an HTTP implementation later touches `api/` only.

**Tech Stack:** Vite 8, React 19, TypeScript, Tailwind CSS 4 (`@tailwindcss/vite`), React Router 7, Recharts 3, Vitest 5 + React Testing Library + jsdom. Fonts: Geist and Geist Mono via `@fontsource-variable/geist` and `@fontsource-variable/geist-mono` (self-hosted, no network dependency).

Spec: `docs/superpowers/specs/2026-09-20-web-frontend-design.md`

## Global Constraints

- Colors, and only these: white `#FFFFFF`, sidebar `#FAFAFA`, ink `#0A0A0A`, muted `#8C8C8C`, faint `#BDBDBD`, hairlines `#E5E5E5` and `#EFEFEF`, fill `#F4F4F4`. No gradients, no shadows.
- Geist weights 400 and 500 only. Numbers and stats in Geist Mono. Headlines use negative tracking.
- At most one ink-filled button per view. Status is shape, not color: filled dot running, hollow dot done, crossed dot failed.
- Copy: sentence case, verb-first buttons, no "please", no "successfully", no exclamation marks.
- Components never import `api/mock.ts` or `api/fixtures.ts`; they use `useApi()` and the hooks.
- Sidebar 240px; below 768px it is a slide-over. Mission thread max-width 720px.
- Transitions 150ms; nothing decorative.
- Commits: short imperative subject, no AI attribution, no trailers. Never push.
- `kingdom/` (pygame) is untouched.

## File Structure

```
web/
  index.html                 shell, title "kingdom", favicon link
  public/castle.svg          favicon (same path data as CastleLogo)
  package.json, vite.config.ts, tsconfig*.json
  src/
    main.tsx                 mounts <App/> with the singleton mock api
    App.tsx                  ApiProvider + routes
    index.css                Tailwind import, @theme tokens, base styles
    types.ts                 domain types
    format.ts                formatElapsed, formatP, formatSynced
    test/setup.ts            jest-dom + ResizeObserver stub
    test/render.tsx          renderWithApp(ui, {api, route})
    api/index.ts             Api interface, ValidationError, ApiProvider, useApi
    api/mock.ts              createMockApi({ stepMs, seed })
    api/fixtures.ts          seedMissions, seedDatasets, EXAMPLE_PROMPTS, buildResult
    hooks/useApiData.ts      useMissions, useMission, useDatasets
    components/              CastleLogo, StatusDot, AppShell, Sidebar, Composer,
                             DatasetChips, StepList, ResultCard, SeriesChart,
                             StatRow, DatasetTable, LinkDatasetDialog
    pages/                   NewMissionPage, MissionPage, DatasetsPage
```

## Contracts (shared by every task)

```ts
// types.ts
export type MissionStatus = 'running' | 'done' | 'failed'
export type StepKey = 'plan' | 'pull' | 'test' | 'chart' | 'writeup'
export type StepState = 'pending' | 'active' | 'done'
export interface MissionStep { key: StepKey; label: string; state: StepState }
export interface SeriesPoint { date: string; a: number; b: number }
export interface MissionResult {
  seriesA: string; seriesB: string; points: SeriesPoint[]
  correlation: number; bestLagDays: number; pValue: number; n: number
  note: string; verdict: string
}
export interface Mission {
  id: string; title: string; hypothesis: string; status: MissionStatus
  datasetIds: string[]; createdAt: string; elapsedSeconds: number
  steps: MissionStep[]; result?: MissionResult; error?: string
}
export interface Dataset {
  id: string; name: string; url: string
  seriesCount: number; dateRange: string; syncedAt: string
}

// api/index.ts
export interface Api {
  listMissions(): Promise<Mission[]>                    // newest first
  getMission(id: string): Promise<Mission | undefined>
  createMission(input: { hypothesis: string; datasetIds: string[] }): Promise<Mission>
  listDatasets(): Promise<Dataset[]>
  linkDataset(input: { name: string; url: string }): Promise<Dataset>
  subscribe(listener: () => void): () => void           // returns unsubscribe
}
export class ValidationError extends Error { field: 'name' | 'url' | 'hypothesis' }
```

Step labels, in order: `plan` "Planned the test", `pull` "Pulled the data", `test` "Ran the permutation test", `chart` "Drew the chart", `writeup` "Wrote up the findings". Active steps render the present-tense form: "Planning the test", "Pulling the data", "Running the permutation test", "Drawing the chart", "Writing up the findings".

---

### Task 1: Remove the terminal

**Files:**
- Delete: `terminal/` (whole folder)
- Rename: `tests/test_terminal.py` → `tests/test_monitor.py`
- Modify: `main.py` (the `terminal` subparser, lines 28-34, and the `elif args.command == "terminal":` branch), `README.md` (command-table row and the `## Terminal` section)

- [ ] **Step 1:** Record the baseline: `.venv/bin/python -m pytest -q 2>&1 | tail -5`. Note pass/fail counts so later failures can be classified as pre-existing or new.
- [ ] **Step 2:** `git mv tests/test_terminal.py tests/test_monitor.py`. In it, remove the `from terminal.app import ...` line and delete exactly the tests that use `create_app`, `index_html`, or `write_snapshot`: `test_api_state`, `test_api_run_and_traversal`, `test_run_files`, `test_index_and_snapshot_routes`, `test_index_html_embeds_state`, `test_write_snapshot`. Read `test_run_details_fall_back_to_status_scores` and `test_real_root_fast`: keep each if it only needs `monitor`, delete it if it needs the Flask app. Remove imports and helpers left unused.
- [ ] **Step 3:** `git rm -r terminal`; delete the subparser block and the `elif` branch in `main.py`; delete the README table row and the whole `## Terminal` section up to the next `## ` heading.
- [ ] **Step 4:** Verify: `grep -rn "terminal" --include="*.py" . | grep -v .venv` shows no imports of the `terminal` package; `.venv/bin/python main.py --help` runs; `.venv/bin/python -m pytest -q` matches the baseline minus the deleted tests, with no new failures.
- [ ] **Step 5:** Commit: `Remove terminal UI, keep monitor tests`.

### Task 2: Scaffold `web/` with tokens and the logo

**Files:** everything under `web/` listed above except `api/`, `hooks/`, `pages/`, and components other than `CastleLogo`. Modify root `.gitignore` to add `web/node_modules/` and `web/dist/`.

**Produces:** `CastleLogo({ size?: number, className?: string })`; Tailwind theme tokens `ink`, `muted`, `faint`, `line`, `line-soft`, `fill`, `side` (usable as `text-ink`, `border-line`, `bg-fill`, ...); font utilities `font-sans` (Geist) and `font-mono` (Geist Mono); `npm run dev | build | test`.

- [ ] **Step 1:** `npm create vite@latest web -- --template react-ts`, then install `react-router-dom recharts @fontsource-variable/geist @fontsource-variable/geist-mono` and dev deps `tailwindcss @tailwindcss/vite vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom`. Delete the template's `App.css`, `assets/`, and demo markup.
- [ ] **Step 2:** `vite.config.ts`: plugins `react()` and `tailwindcss()`; `test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', globals: true }`. Add `"test": "vitest run"` to `package.json`; add `vitest/globals` and `@testing-library/jest-dom` to tsconfig `types`.
- [ ] **Step 3:** `src/index.css`:

```css
@import "tailwindcss";
@import "@fontsource-variable/geist";
@import "@fontsource-variable/geist-mono";

@theme {
  --font-sans: "Geist Variable", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "Geist Mono Variable", ui-monospace, monospace;
  --color-ink: #0a0a0a;
  --color-muted: #8c8c8c;
  --color-faint: #bdbdbd;
  --color-line: #e5e5e5;
  --color-line-soft: #efefef;
  --color-fill: #f4f4f4;
  --color-side: #fafafa;
}

body { @apply bg-white font-sans text-ink antialiased; }
```

- [ ] **Step 4:** Write the failing test `CastleLogo.test.tsx`: renders an `svg` with accessible name "kingdom" and honours `size`. Run `npm test` — fails (no component). Implement `CastleLogo` with a 16×16 viewBox and the single path `M1 2h3v2h2V2h4v2h2V2h3v13h-5v-4a2 2 0 0 0-4 0v4H1z`, `fill="currentColor"`. Copy the same path into `public/castle.svg` with `fill="#0a0a0a"`; link it as the favicon; set `<title>kingdom</title>`.
- [ ] **Step 5:** `src/test/setup.ts` imports `@testing-library/jest-dom/vitest` and stubs `ResizeObserver` (Recharts needs it in jsdom).
- [ ] **Step 6:** `npm test` passes, `npm run build` passes. Commit: `Scaffold web app with design tokens and castle logo`.

### Task 3: Types, fixtures, mock API

**Files:** `src/types.ts`, `src/format.ts`, `src/api/index.ts`, `src/api/fixtures.ts`, `src/api/mock.ts`; tests `src/api/mock.test.ts`, `src/format.test.ts`.

**Produces:** the Contracts above, plus `createMockApi(opts?: { stepMs?: number; seed?: { missions: Mission[]; datasets: Dataset[] } }): Api` (default `stepMs` 2500, default seed from fixtures), `ApiProvider({ api, children })`, `useApi(): Api`, `EXAMPLE_PROMPTS: string[]` (three), `formatElapsed(seconds)` → `"4m 12s"` / `"38s"`, `formatP(p)` → `"0.002"` or `"<0.001"`, `formatSynced(iso, now?)` → `"2h ago"` / `"1d ago"` / `"just now"`.

Mock behaviour: `createMission` trims the hypothesis, throws `ValidationError('hypothesis')` if empty, derives `title` (first 48 chars at a word boundary, trailing punctuation stripped), creates a `running` mission with `plan` active and the rest pending, prepends it, notifies, and schedules a tick every `stepMs`: each tick marks the active step done and activates the next, adds `stepMs/1000` scaled elapsed seconds, notifies; after `writeup` completes, status becomes `done` with `buildResult(hypothesis)` (deterministic from a string hash so the same prompt gives the same chart). Seeded running missions also tick. `linkDataset` trims, throws `ValidationError('name')` on empty name and `ValidationError('url')` unless `new URL(url)` parses with protocol `http:` or `https:`. All getters return copies, never internal references.

Fixtures, modelled on `missions/runs/`: running — "Tanker chatter vs Brent range" (on `test`), "Tehran wind vs PM2.5" (on `pull`); done — "Iran events vs Brent returns", "Goldstein tone vs VIX", "Houston heat vs Henry Hub gas", "Dubai NO2 vs Brent", "Protest events vs gold"; failed — "Houston air quality vs Gulf Coast" with error "No air-quality series found for the US Gulf Coast."; datasets — GDELT events, Yahoo Finance, Open-Meteo weather, CAMS air quality, with real source URLs. Include at least one done mission with a null-ish finding (|r| < 0.1, p > 0.3, verdict "No reliable link.") so the UI is honest about negatives.

- [ ] **Step 1:** Write `mock.test.ts` with `vi.useFakeTimers()`: lists seeds newest first; `createMission` returns running with plan active; advancing `stepMs` four times walks the active step through all keys; a fifth tick yields `done` with a result and `elapsedSeconds > 0`; same hypothesis gives an identical result; `subscribe` fires on create and on each tick and stops after unsubscribe; empty/whitespace hypothesis rejects with `ValidationError` field `hypothesis`; `getMission('nope')` resolves `undefined`; mutating a returned mission does not change the store; `linkDataset` adds a row at the top, rejects empty name, rejects `ftp://x`, rejects `not a url`, accepts `https://`. Write `format.test.ts` for the boundaries: 0s, 59s, 60s, 3599s; p = 0.0004, 0.002, 0.5; 30s, 2h, 26h ago.
- [ ] **Step 2:** `npm test` — fails on missing modules.
- [ ] **Step 3:** Implement the five files.
- [ ] **Step 4:** `npm test` passes; `npm run build` passes. Commit: `Add domain types, fixtures, and mock API`.

### Task 4: App shell, sidebar, routing

**Files:** `src/hooks/useApiData.ts`, `src/components/{StatusDot,Sidebar,AppShell}.tsx`, `src/App.tsx`, `src/main.tsx`, `src/test/render.tsx`, placeholder pages; tests `Sidebar.test.tsx`, `StatusDot.test.tsx`.

**Produces:** `useMissions(): Mission[] | undefined`, `useMission(id): { mission?: Mission; loading: boolean }`, `useDatasets(): Dataset[] | undefined` — each loads on mount and reloads on `api.subscribe`. `StatusDot({ status })` with `aria-label` "Running" / "Done" / "Failed". `renderWithApp(ui, { api?, route? })` wraps in `ApiProvider` + `MemoryRouter`. Routes: `/` → NewMissionPage, `/missions/:id` → MissionPage, `/datasets` → DatasetsPage, all inside `AppShell`.

Sidebar layout: 240px, `bg-side`, right hairline. Logo + wordmark (15px, weight 500, tracking tight) link to `/`. "New mission" outline button (white bg, `border-line`, 8px radius) links to `/`. Section labels "Running" and "Done" in 12px muted; a section is omitted when empty. Rows: 13px, 6px radius, hover `bg-fill`, active `bg-[#F0F0F0]` with `aria-current="page"`; done/failed rows use muted text. "Datasets" pinned at the bottom above a top hairline. Below 768px the sidebar is hidden; a top bar shows a menu button and the logo; the menu opens the sidebar as a slide-over with a scrim; it closes on navigation, scrim click, and Escape.

- [ ] **Step 1:** Tests: running missions listed under "Running", done and failed under "Done"; section omitted when empty; the row for the current route has `aria-current`; "Datasets" and "New mission" links point to the right routes; a newly created mission appears without remounting (subscribe works); StatusDot labels.
- [ ] **Step 2:** Run — fail. **Step 3:** Implement. **Step 4:** `npm test`, `npm run build` pass.
- [ ] **Step 5:** Commit: `Add app shell, sidebar, and routing`.

### Task 5: New mission page

**Files:** `src/components/{Composer,DatasetChips}.tsx`, `src/pages/NewMissionPage.tsx`; tests alongside.

**Produces:** `Composer({ datasets, onSubmit, value, onChange })` where `onSubmit(hypothesis: string, datasetIds: string[])`; `DatasetChips({ datasets, selected, onToggle })`, chips are `button[aria-pressed]`.

Layout: column centered vertically and horizontally, max-width 640px. Headline "What should we look into?" 32px / weight 500 / tracking -0.03em. Composer: `border-line`, 16px radius, focus-within border ink; auto-growing textarea (placeholder "Describe a connection to test"), bottom row with chips on the left and a 32px round ink submit button (`aria-label="Start mission"`, up-arrow icon) on the right; button is faint when the prompt is empty. Selected chip: ink text, `border-line`; unselected: muted text with line-through off, `border-line-soft`. Below: label "Try one" and the three `EXAMPLE_PROMPTS` as hairline rows that fill the composer and focus it.

- [ ] **Step 1:** Tests: Enter submits and navigates to `/missions/<new id>`; Shift+Enter inserts a newline and does not submit; empty and whitespace-only prompts do not call `createMission`; clicking an example fills the textarea; all chips pressed by default; toggling one off removes its id from the submitted `datasetIds`; page renders with zero datasets.
- [ ] **Step 2–4:** fail → implement → pass, build passes.
- [ ] **Step 5:** Commit: `Add new mission page`.

### Task 6: Mission page

**Files:** `src/components/{StepList,ResultCard,SeriesChart,StatRow}.tsx`, `src/pages/MissionPage.tsx`; tests alongside.

**Produces:** `StepList({ steps, status, elapsedSeconds })`, `ResultCard({ result })`, `SeriesChart({ result })`, `StatRow({ result })`.

Layout: column max-width 720px, 48px top padding. Hypothesis bubble right-aligned, `bg-fill`, 18px radius, max-width 80%. StepList while running: one line per non-pending step, done steps muted with a check icon, the active step in ink with a 150ms-eased spinner and present-tense label. When status is `done` or `failed`: a single `button` "Worked for 4m 12s" with a chevron, `aria-expanded`, collapsed by default, expanding to the full list. ResultCard: `border-line`, 12px radius, 20px padding — legend (ink line = seriesA, gray line = seriesB, 12px muted), SeriesChart 220px tall (Recharts `LineChart`, no grid, no dots, 1.5px strokes `#0A0A0A` and `#BDBDBD`, muted 11px mono axis ticks, hairline tooltip), StatRow (Correlation, Best lag, p-value, Sample — labels 12px muted, values 18px mono), hairline, note as 15px / 1.65 prose paragraphs, then the verdict line at weight 500. Failed: a hairline card with "This mission failed" and the error text. Unknown id: "Mission not found" with a "Start a new mission" link. While loading render nothing (avoids a not-found flash).

- [ ] **Step 1:** Tests: running mission shows expanded steps with the active one marked `aria-current="step"` and no result card; done mission shows the collapsed "Worked for" button, expands on click to five steps, and shows stats formatted via `formatP` and the verdict; failed mission shows the error and no chart; unknown id shows not-found; a running mission re-renders to done after fake timers advance (subscribe path); note with two paragraphs renders two `<p>`.
- [ ] **Step 2–4:** fail → implement → pass, build passes.
- [ ] **Step 5:** Commit: `Add mission thread page`.

### Task 7: Datasets page

**Files:** `src/components/{DatasetTable,LinkDatasetDialog}.tsx`, `src/pages/DatasetsPage.tsx`; tests alongside.

Layout: column max-width 880px. Header row: "Datasets" 24px / 500 / tight tracking, and the "Link dataset" ink pill (the view's single filled button). Sub-line in muted 14px: "Sources your missions can draw on." Table: header row 12px muted, rows 14px with `border-line-soft` dividers, 14px vertical padding; columns Name, Source (hostname as an external link, `target="_blank" rel="noreferrer"`), Series (mono, right-aligned), Range (muted), Synced (muted, via `formatSynced`). Below 640px hide Range and Series. Dialog: native `<dialog>` opened with `showModal()`, 400px, 16px radius, hairline border, scrim `rgba(10,10,10,0.2)`; fields Name and URL (placeholder `https://`), inline 13px error text under the offending field from `ValidationError.field`, buttons "Cancel" (ghost) and "Link dataset" (ink). Closing resets the form. Empty state: "Link your first dataset" + one line + the same button.

- [ ] **Step 1:** Tests: renders the four fixture rows with hostnames; linking a valid dataset closes the dialog and the row appears first; empty name shows "Enter a name"; `ftp://x` shows "Enter an http or https URL"; errors clear on edit; Cancel closes and reopening shows empty fields; empty seed shows the empty state. jsdom lacks `showModal` — polyfill it in `test/setup.ts` (set/remove the `open` attribute).
- [ ] **Step 2–4:** fail → implement → pass, build passes.
- [ ] **Step 5:** Commit: `Add datasets page`.

### Task 8: Docs and visual verification

**Files:** `README.md` (add a `## Web` section where Terminal was: what it is, `cd web && npm install && npm run dev`, note that it runs on mock data in `web/src/api/`), `web/README.md` replaced with four lines pointing at the spec, `.claude/launch.json` (dev server entry, port 5173).

- [ ] **Step 1:** Write the docs. Add `.claude/launch.json` with `{ name: "web", runtimeExecutable: "npm", runtimeArgs: ["run","dev","--prefix","web"], port: 5173 }`.
- [ ] **Step 2:** Start the preview. Check console for errors. Walk the flow: submit a mission, watch it run to done, expand steps, open a failed mission, link a dataset, hit an unknown mission URL.
- [ ] **Step 3:** Screenshot each view at desktop width and at the mobile preset; fix spacing, alignment, and overflow defects found; confirm no horizontal scroll at 375px and that the slide-over opens and closes.
- [ ] **Step 4:** Final gates: `npm test`, `npm run build`, `.venv/bin/python -m pytest -q`. Report real output.
- [ ] **Step 5:** Commit: `Document web app`.
