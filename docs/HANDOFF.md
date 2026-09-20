# Handoff — Kingdom web app and Devin missions

Updated 2026-09-20 after the local integration and polish pass.
Pick up on branch **`devin-backend`**.

## What Kingdom is

You link datasets, start a **mission** (a question), and Devin researches it
autonomously. The app shows progress summaries, steps, visual artifacts and a
persistent working spinner as they arrive. Messages steer the same session while
running or afterward. Routine decisions do not require approval; completion
automatically produces a **report** (a typeset, shareable summary) and closes the
run. An **explorer** can be requested separately (a small interactive site Devin writes for that
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
docker compose up --build -d          # real Devin, no app ACU cap
# UI: http://localhost:5173, API: http://localhost:8030
```

The original Python/Vite commands still work at ports 8030/5173. See README
and AGENTS.md for container checks. Base Compose uses the local live DB.

**Current running configuration:** Live Devin with no Kingdom-imposed ACU cap; Tom authorized removing the limit after it stopped a mission.
`docker compose up -d` uses the same two containers and the existing `.kingdom`
live database. The `compose.demo.yaml` override provides the isolated scripted
demo when explicitly wanted. No test mission was launched for this switch.

**Demo mode** (no key, or `KINGDOM_FAKE_DEVIN=1`): a scripted fake Devin plays
a full mission, a report, and an explorer. Free. **Live mode**: a v3
service-user key (`cog_…`) in `.env` as `DEVIN_API_KEY`; each mission is one
Devin session with optional `KINGDOM_MAX_ACU` (0 means no app cap) in `KINGDOM_DEVIN_MODE` (`fast`).
The key exists only in the local, gitignored `.env`. v1 endpoints reject it, so
the old CLI's `--brain devin` does not work with it; only `server/` does.

## Branches (all on GitHub unless noted)

| Branch | State |
| --- | --- |
| `main` | Green and verified from a fresh clone: live Devin backend, mission thread + artifacts + reply, dark mode, `research/`. **No** report or explorer |
| `devin-backend` | Includes local merges of `main` (`6422a21`) and `dataset-cards` (`322980d`), reports, explorers, research picker and polish. Changes remain local; no push or landing on `main` during this pass. |
| `dataset-cards` | Integrated into `devin-backend`; cards now use theme tokens in dark mode. |
| `research-snapshot` | Same research commit that is already on `main` |

The local `main` research folder, pytest `testpaths = tests`, and README are
integrated. Dark-mode conflicts preserved the newer shared theme store and
report print styles. Remote refs were not refreshed; inspect them before a
future push or landing.

## State of `devin-backend`

Latest offline checks in Docker: **Python 1,195 passed / 3 skipped** across
`tests`; **web 624 passed**. Production build and `oxlint` clean. The full
Python run emits one existing SciPy precision warning for a constant-valued
step-change fixture. No live Devin credits spent during this pass.

Done and working:

- **App controls.** Theme switch is in the top-right header on desktop and mobile.
  The sidebar mode label is removed; this does not change the configured backend.

- **Report.** Report tab → "Generate report" → Devin fills a structured report
  → typeset page with key figures re-rendered from the thread, "Ask next"
  questions that prefill a reply, Copy link, Regenerate, Export PDF (print
  stylesheet forces light). Verified end to end in demo mode only.
- **Mission tabs** Thread · Report · Explorer, shared header.
- **Research attachment UI.** New mission → Attach research → search 111 saved
  findings from 13 collections, or paste notes. Full evidence/caveats travel
  through `reference`; the question remains editable and the attachment can be
  removed. `GET /api/research` uses the reviewed `research/library.json`; legacy
  `research/*/findings.json` is used only when that index is absent. The index is
  copied from `explore/packaging/frontend/findings_index.json`, not its stale root
  index. Refresh instructions and snapshot limitations are in `research/README.md`.
- **Recovery and polish.** Visible submission errors and retry for missions,
  dataset linking and reports; loading/reconnecting states instead of blank
  mission/dataset pages; reduced motion; theme-aware dataset thumbnails.
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

### Resolved: the explorer map now renders inside the sandbox

The old MapLibre implementation produced a blank or frozen framed map.
Leaflet now renders in the real product iframe under the server's production
CSP, with **no sandbox relaxation**. Verified standalone and framed using the Codex in-app browser:
gray basemap, point selection and evidence, live theme sync, dark heatmap,
satellite imagery, zoom, 375px layout, bottom sheet, slider extremes and reset.

The basemaps are Esri gray (light/dark) and World Imagery, with canvas points
and an ink heatmap. GUIDE.md already contained the WebGL/worker warning.
Browser testing found and fixed a literal `false` in the empty-filter view;
the map also observes container resizing when the mobile sheet expands.
The report's "Ask next" links were actually absent despite the earlier notes;
they are now implemented and covered by navigation/send tests.

Use demo mission `m_46bd8f7f`, explorer version 2, in the Compose volume for the browser walkthrough.
It is synthetic: fake Devin always delivers the sample Kharkiv explorer,
regardless of the mission question. The local live database is untouched.

### Not yet tested against real Devin

1. **Report and explorer on a real session.** Devin's structured-output schema
   is fixed at session creation. The one live mission (`m_f064f4d0`, "Houston
   heat vs gas prices", in `.kingdom/kingdom.db`) predates the `report` and
   `explorer` fields, so they may only work on **new** missions.
2. **The explorer request is ~79 KB** (guide + full kit text; example data is
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

Prepared `tests/server/test_live_delivery.py` to exercise a new five-location
hydropower mission, report and explorer in one capped session. It requires
`-m live`, `DEVIN_API_KEY` and an explicitly approved positive
`KINGDOM_LIVE_DELIVERY_MAX_ACU`. Run that file alone so the separate smoke test
does not add another session. API delivery success does not prove the generated
site works; inspect its saved files in the browser afterward. No new live
session has been launched. The final user direction prioritizes hackathon
frontend polish and speed; live validation is an optional follow-up.

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
  server and brief; the New mission research picker now attaches one.
- `web/src/types.ts` and `web/src/api/index.ts` are the contract between web
  and server. Change them deliberately, both sides together.
- The repo rule for this project: commit locally, never push or merge without
  being asked; no AI attribution in commits.

## Suggested next steps, in order

1. Once an ACU budget is approved, run the opt-in live-delivery check. Verify
   narration, structured output and acceptance of the full kit message.
2. Inspect the real delivered explorer and report in the browser. A subsequent
   mission can use a fix-list finding from the research library or pasted notes.
3. Review the local integration commits, then push/land only when requested.
