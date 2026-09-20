# Handoff — Kingdom web app and Devin missions

Written 2026-09-20. Everything below is committed; the working tree is clean.
Pick up on branch **`devin-backend`**.

## What Kingdom is

You link datasets, start a **mission** (a question), and Devin researches it
live. The app shows Devin's thinking as prose, its steps, and visual artifacts
as they are produced; you reply to steer it like a chat and mark it done when
satisfied. Each mission can then produce a **report** (a typeset, shareable
summary) and an **explorer** (a small interactive site Devin writes for that
mission, for findings that are places rather than statistics — the motivating
example is "which buildings in Ukraine likely have asbestos roofs").

Visual system: white-and-grotesk, YC-style. Geist 400/500, Geist Mono for
numbers, ink + two grays + hairlines, no colour, no shadows, dark mode is the
same palette turned over. Rules live in
`docs/superpowers/specs/2026-09-20-web-frontend-design.md`.

## Where things are

| Path | What |
| --- | --- |
| `web/` | React 19 + Vite + TypeScript + Tailwind 4 app. `npm run dev` → :5173, proxies `/api` to :8030 |
| `server/` | Flask + SQLite API and Devin poller. `python main.py serve` → :8030 |
| `server/explorer_kit/` | Design system + helpers + worked example + `GUIDE.md` that Devin builds explorers from |
| `research/` | 40 MB snapshot (scripts, `IDEAS.md`, reports, findings, figures) of the team's 21 GB `explore/` folder, which is **not** in git |
| `docs/superpowers/specs/`, `plans/` | Design specs and the implementation plan. The plan's two addenda (report; explorer) are the **frozen contracts** |
| `kingdom/` | Older pygame dashboard, untouched |

Run it:

```bash
python main.py serve                  # demo mode if no DEVIN_API_KEY
cd web && npm install && npm run dev
```

**Demo mode** (no key, or `KINGDOM_FAKE_DEVIN=1`): a scripted fake Devin plays
a full mission, a report, and an explorer. Free. **Live mode**: a v3
service-user key (`cog_…`) in `.env` as `DEVIN_API_KEY`; each mission is one
Devin session capped by `KINGDOM_MAX_ACU` (5) in `KINGDOM_DEVIN_MODE` (`fast`).
The key exists only in the local, gitignored `.env`. v1 endpoints reject it, so
the old CLI's `--brain devin` does not work with it; only `server/` does.

## Branches (all on GitHub unless noted)

| Branch | State |
| --- | --- |
| `main` | Green and verified from a fresh clone: live Devin backend, mission thread + artifacts + reply, dark mode, `research/`. **No** report or explorer |
| `devin-backend` | `main` + report + explorer. Local is **1 commit ahead of GitHub** (`8c03d33`, the unverified Leaflet swap). `git push origin devin-backend` to back it up |
| `dataset-cards` | Card view with generated thumbnails for the Datasets page. Finished, never merged; will conflict lightly with `devin-backend` in `types.ts`, `mock.ts`, `fixtures.ts` |
| `research-snapshot` | Same research commit that is already on `main` |

`devin-backend` has diverged from `main`: `main` also carries the research
folder, a `pytest.ini` `testpaths = tests` line, and a README section. Merge or
rebase before landing; without that `pytest.ini` line, pytest would try to
collect `research/polymarket_experts/tests`.

## State of `devin-backend`

Gates at the last commit: **Python 1,050 passed / 1 skipped** (`pytest
tests/server`), **web 573 passed**, `tsc -b` clean, `oxlint` clean.

Done and working:

- **Report.** Report tab → "Generate report" → Devin fills a structured report
  → typeset page with key figures re-rendered from the thread, "Ask next"
  questions that prefill a reply, Copy link, Regenerate, Export PDF (print
  stylesheet forces light). Verified end to end in demo mode only.
- **Mission tabs** Thread · Report · Explorer, shared header.
- **Explorer plumbing.** "Build explorer" / "Request a change" → message to
  the same Devin session → Devin attaches `explorer-v<N>.zip` → server
  downloads, unpacks as hostile input (zip-slip, bombs, symlinks, type
  allowlist, size caps), stores each version, serves it with sandbox headers →
  web shows it in `<iframe sandbox="allow-scripts allow-popups …">` (never
  `allow-same-origin`) with live light/dark sync. Verified in demo mode in real
  Chrome: framed, themed, kit and data load, panel/slider/ranked list work.
- **Attachment downloads fixed.** The `url` Devin's API returns
  (`app.devin.ai/attachments/…`) rejects API keys. The working route is
  `GET /v3/organizations/{org}/attachments/{id}/{name}` → 307 to signed S3,
  followed without credentials. Devin's raw `ATTACHMENT:{…}` chat lines are
  stripped from the thread.

### The open bug: the explorer's map is blank inside the sandbox

Served as a plain page, the kit's asbestos example is excellent (gray Kharkiv
basemap, ink dots sized by likelihood). Inside the sandboxed frame the map area
is blank and the framed page froze in Chrome. Cause: the kit used **MapLibre
GL**, whose web workers do not survive an opaque origin. The sandbox is a
deliberate security boundary (AI-written code inside the app) and should not be
relaxed.

Fix in progress, commit `8c03d33`, **never run**: `kit.js` and `kit.css` are
converted to **Leaflet** (no workers, no WebGL; CARTO light/dark raster tiles,
Esri satellite, canvas renderer for points, ink heatmap). `index.html` and
`GUIDE.md` are only partly updated (`GUIDE.md` still mentions MapLibre once;
check `index.html` calls match the new `Kingdom.map` surface). `node --check
kit.js` passes; nothing else is known about it.

To finish: make the example work standalone, then verify **inside a sandboxed
iframe under the production CSP** — the agent brief in the session did this
with a scratch dir (`index.html`, `data.json`, `kit/kit.css`, `kit/kit.js`,
and a `host.html` that iframes it with the sandbox attribute), a tiny Python
server adding the CSP header, and headless Chrome screenshots (Leaflet needs no
WebGL, so headless works). Check light, dark, heatmap, satellite, 375px. Then
update `GUIDE.md` to say WebGL/worker map libraries (MapLibre, Mapbox GL,
deck.gl) do not work in explorers.

### Not yet tested against real Devin

1. **Report and explorer on a real session.** Devin's structured-output schema
   is fixed at session creation. The one live mission (`m_f064f4d0`, "Houston
   heat vs gas prices", in `.kingdom/kingdom.db`) predates the `report` and
   `explorer` fields, so they may only work on **new** missions.
2. **The explorer request is ~65 KB** (guide + full kit text; example data is
   cut to 20,000 chars by `MAX_KIT_DATA_CHARS` in `server/brief.py`). Whether
   Devin's message endpoint accepts that is unknown. Fallback: have Devin fetch
   the kit from this repo on GitHub instead of inlining it.
3. **A real explorer needs place-level results.** The Houston mission has
   nothing to map. The natural first case is one of the fix-list findings in
   `research/` (see the table at the top of `research/IDEAS.md`), brought in
   through a mission's `reference` field.
4. The brief was strengthened after the first live run (narrate before/after
   every step, update structured output one step at a time). Not re-tested
   live.

Live Devin spend so far: one 1-ACU smoke test, one mission capped at 5 ACU, a
few cheap follow-up messages.

## Things that will bite you

- **`'self'` in a CSP matches nothing in an opaque-origin sandbox.** The
  explorer policy therefore names the real origin (`explorer_csp` /
  `browser_origin` in `server/app.py`), taken from a validated
  `X-Forwarded-Host`; the Vite proxy sends it (`xfwd: true`). Any reverse proxy
  in front of the server must do the same.
- The `Store` resolves its db path to absolute on purpose: Flask's `send_file`
  resolves relative paths against the `server/` package, not the cwd.
- The Claude desktop **preview pane blocks subrequests from sandboxed pages**
  (`ERR_BLOCKED_BY_CLIENT`). That is the pane, not the app; use real Chrome or
  headless Chrome to look at explorers.
- Headless Chrome cannot draw MapLibre/WebGL maps reliably, and
  `--virtual-time-budget` leaves nested frames unpainted.
- Replication: a mission's `reference` is prior research Devin retraces
  silently as its own investigation, never mentioning it, but it must really
  run the analyses and follow the data if it diverges. Wired end to end in the
  server and brief; there is **no UI** to attach one yet.
- `web/src/types.ts` and `web/src/api/index.ts` are the contract between web
  and server. Change them deliberately, both sides together.
- The repo rule for this project: commit locally, never push or merge without
  being asked; no AI attribution in commits.

## Suggested next steps, in order

1. Finish and verify the Leaflet kit inside the sandbox (above). Push.
2. Run one **new** live mission, then Generate report on it — settles unknown 1
   for reports cheaply (well under 1 ACU on top of the mission).
3. Run a live mission with place-level results (a fix-list idea via
   `reference`), then Build explorer — settles unknowns 1–3. Watch the first
   request for a message-size rejection.
4. Merge `main` into `devin-backend` (research, `pytest.ini`), then land it on
   `main`; merge `dataset-cards`.
5. Build the UI for attaching a `reference` / importing a finding from
   `research/*/findings.json`.
