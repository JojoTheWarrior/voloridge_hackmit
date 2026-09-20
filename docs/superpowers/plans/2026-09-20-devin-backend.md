# Live Missions with Devin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Starting a mission creates a real Devin session; the app streams its thoughts, steps, and visual artifacts, lets the user reply, and lets them mark it done.

**Architecture:** A Flask + SQLite server in `server/` owns missions and polls Devin's v3 API through a `DevinClient` protocol (real `V3DevinClient`, scripted `FakeDevin` when no key is set). A pure `sync` function turns Devin snapshots into ordered thread events. The React app swaps its mock for an HTTP `Api` and renders the thread and typed artifacts.

**Tech Stack:** Python 3.13, Flask, sqlite3, requests, pytest. React 19, TypeScript, Tailwind 4, Recharts, Vitest.

Spec: `docs/superpowers/specs/2026-09-20-devin-backend-design.md` (read it fully; it is the source of truth for behaviour). Visual rules: `docs/superpowers/specs/2026-09-20-web-frontend-design.md`.

## Global Constraints

- The contract below is frozen. `web/src/types.ts` and `web/src/api/index.ts` are already written and must not be edited; if something in them is wrong, stop and report rather than changing it.
- The server emits **camelCase JSON** exactly matching `web/src/types.ts`. Devin's structured output is snake_case; the server normalises it.
- Never print, log, commit, or echo `DEVIN_API_KEY`. Never read `.env` contents into output. Tests must never call the real Devin API (the one `live`-marked test is run manually by the lead only).
- Python: match the repo's style (`from __future__ import annotations`, type hints, small modules, docstrings only where non-obvious). No new Python dependencies beyond what `requirements.txt` has.
- Web colors, and only these: white, `#FAFAFA`, ink `#0A0A0A`, muted `#8C8C8C`, faint `#BDBDBD`, hairlines `#E5E5E5` / `#EFEFEF`, fill `#F4F4F4` (Tailwind tokens `ink`, `muted`, `faint`, `line`, `line-soft`, `fill`, `side`). Geist 400/500 only, numbers in `font-mono`, no shadows, no gradients, 150ms transitions, sentence case, no exclamation marks, at most one ink-filled button per view.
- Web code style: no semicolons, single quotes, named exports, small focused files, comments only for non-obvious "why". Components never import `api/mock.ts` or fixtures; they use `useApi()` and hooks.
- TDD: write the failing test, watch it fail, implement, watch it pass. Cover edge cases and error paths, not just the happy path.
- Agents share one working tree. Touch only the files your task owns. Do **not** run any `git` command that changes state (no add, commit, checkout, stash, reset, merge, push). The lead commits.
- While other agents are mid-work the full web build may be red because of their files. Judge your own work by running your own test files (`npx vitest run <paths>`, `pytest tests/server`), and report honestly what you ran.

## Contract

### HTTP (all under `/api`, JSON, camelCase)

```
GET  /api/meta                        -> {"demo": true}
GET  /api/missions                    -> [MissionSummary]            newest first
POST /api/missions                    {"hypothesis","datasetIds":[],"reference"?} -> 201 Mission
GET  /api/missions/:id                -> Mission | 404 {"message"}
POST /api/missions/:id/messages       {"text"} -> 202 {}             reopens a done mission
POST /api/missions/:id/done           -> 200 {}
GET  /api/missions/:id/attachments/:name -> image bytes | 404
GET  /api/datasets                    -> [Dataset]
POST /api/datasets                    {"name","url"} -> 201 Dataset
422 on validation: {"field": "hypothesis|text|name|url", "message": "..."}
```

Validation messages (exact): hypothesis empty → "Describe a connection to test"; text empty → "Write a reply"; name empty → "Enter a name"; url not http/https → "Enter an http or https URL".

Shapes are exactly `MissionSummary`, `Mission`, `MissionEvent`, `Artifact`, `Dataset`, `Meta` in `web/src/types.ts`. `reference` is accepted on create and never returned. Artifact `src` values that were `attachment:<name>` are rewritten by the server to `/api/missions/<id>/attachments/<name>`. Event ids are stable strings; events are returned in thread order.

Example `Mission`:

```json
{"id":"m_8f3a","title":"Storm damage vs power outages","hypothesis":"Do satellite images of storm damage predict how long power outages last?",
 "status":"waiting","createdAt":"2026-09-20T12:00:00Z","updatedAt":"2026-09-20T12:04:10Z",
 "datasetIds":["gdelt"],"sessionUrl":"https://app.devin.ai/sessions/devin-abc","needsUser":"Should I drop the outlier county?",
 "events":[
  {"id":"e1","at":"...","kind":"user_message","text":"Do satellite images..."},
  {"id":"e2","at":"...","kind":"step","stepId":"s1","label":"Read both datasets","state":"done"},
  {"id":"e3","at":"...","kind":"thought","text":"The imagery set has 2,140 tiles..."},
  {"id":"e4","at":"...","kind":"artifact","artifact":{"id":"a1","type":"chart","kind":"scatter","title":"Severe share vs outage hours","headline":"r = 0.58","xLabel":"Severe share","yLabel":"Median outage hours","series":[{"name":"Counties","points":[[0.1,4.2],[0.3,9.1]]}]}},
  {"id":"e5","at":"...","kind":"conclusion","verdict":"A real but modest link.","summary":"...","stats":[{"label":"Correlation","value":"0.58"}]}
 ]}
```

### Python interfaces (server-internal)

```python
# server/devin.py
@dataclass(frozen=True)
class SessionRef:      session_id: str; url: str | None
@dataclass(frozen=True)
class DevinMessage:    id: str; role: str  # "devin" | "user"
                       text: str; at: str
@dataclass(frozen=True)
class Attachment:      name: str; url: str
@dataclass(frozen=True)
class SessionSnapshot: status: str  # "running" | "waiting" | "finished" | "error"  (normalised)
                       detail: str | None; structured_output: dict | None
class DevinUnavailable(RuntimeError): ...
class DevinClient(Protocol):
    def create_session(self, prompt: str, *, title: str, schema: dict, max_acu: int) -> SessionRef: ...
    def get_session(self, session_id: str) -> SessionSnapshot: ...
    def list_messages(self, session_id: str) -> list[DevinMessage]: ...
    def send_message(self, session_id: str, text: str) -> None: ...
    def list_attachments(self, session_id: str) -> list[Attachment]: ...
def make_client() -> tuple[DevinClient, bool]:   # (client, is_demo)
```

---

### Task 1 (agent: server): the whole `server/` package

**Files:** create `server/__init__.py`, `app.py`, `store.py`, `devin.py`, `sync.py`, `poller.py`, `brief.py`, `artifacts.py`; tests in `tests/server/test_*.py` (one per module) plus `tests/server/__init__.py` if the repo's test layout needs it; modify `main.py` (add a `serve` subcommand: `--port` default 8030, `--host` default 127.0.0.1, `--db` default `.kingdom/kingdom.db`), `.gitignore` (add `.kingdom/`), `requirements.txt` only if something is genuinely missing, and register a `live` pytest marker (in `pytest.ini`/`pyproject`/`conftest.py`, whichever the repo already uses, else a new `pytest.ini`).

Build order (each with tests first): `artifacts.py` → `store.py` → `brief.py` → `devin.py` (FakeDevin, then V3DevinClient against stubbed `requests`) → `sync.py` → `poller.py` → `app.py` → `main.py serve`.

Key behaviours beyond the spec text:
- `make_client()` returns `FakeDevin` when `DEVIN_API_KEY` is unset/empty or `KINGDOM_FAKE_DEVIN=1`; load `.env` the way the repo's `warsignal.config.env` does.
- `FakeDevin` advances by wall-clock time since session creation (injectable clock; default about 3s per beat) so that polling it produces a believable live run: 5 steps, 6+ thoughts, one artifact of **every** type (use `https://picsum.photos/seed/<n>/640/420` style URLs for image items), ends `waiting` with a conclusion. A `send_message` produces a scripted Devin reply and one more artifact a few seconds later, then `waiting` again.
- V3 status normalisation: map v3 `status`/`status_detail` values to the four normalised ones. The docs list `new`, `running`, `exit`, `error`, `suspended` among statuses; treat unknown values as `running`, and keep the mapping in one table so the lead can correct it after the live smoke test.
- `V3DevinClient.list_messages` must tolerate both `{"items": [...]}` and a bare list, and unknown message fields; derive `role` defensively.
- `sync` is pure: `sync(mission_row, stored_events, snapshot, messages, attachments) -> SyncResult(new_events, updated_events, status, needs_user)`; the poller applies it to the store. Idempotent.
- The poller is a daemon thread with an injectable `sleep`/clock; `tick()` is callable directly from tests. One failing mission must not stop others syncing.
- Attachment proxy: only names present in the session's attachment list, only `image/*` responses, 10 MB cap, never forwards the Authorization header to non-Devin hosts.
- CORS is not needed (Vite proxies); do not add it.
- Add `tests/server/test_live.py` with one `@pytest.mark.live` test (skipped unless `-m live` and a key is present) that creates a session with a tiny prompt and `max_acu=1`, polls up to 90s for at least one Devin message, and prints the raw status values and message keys it saw. Do **not** run it.

Verification to report: `.venv/bin/python -m pytest tests/server -q` output, `.venv/bin/python -m pytest -q` (whole suite; must stay green apart from the skipped live test), and a manual check that `python main.py serve --port 8031` starts in demo mode with the key hidden (`KINGDOM_FAKE_DEVIN=1`), `curl` of `/api/meta`, create a mission, poll it for ~20s and show events accumulating. Kill the server after.

### Task 2 (agent: web-thread): data layer, sidebar, mission thread

**Files (owned):** `web/src/api/http.ts` (+test), `web/src/api/mock.ts`, `web/src/api/fixtures.ts`, their tests, `web/src/hooks/useApiData.ts`, `web/src/steps.ts` (delete if unused), `web/src/format.ts`, `web/src/main.tsx`, `web/vite.config.ts` (proxy `/api` → `http://127.0.0.1:8030`), `web/src/components/{Sidebar,StatusDot,AppShell}.tsx`, new `web/src/components/thread/*` (`MissionHeader`, `EventList`, `ThoughtEvent`, `StepEvent`, `ConclusionCard`, `ErrorEvent`, `ReplyComposer`, `WorkLog` for the folded history), `web/src/pages/{MissionPage,NewMissionPage,DatasetsPage}.tsx` and their tests, `web/src/test/*`. Delete the now-unused `StepList`, `ResultCard`, `StatRow`, `SeriesChart` **only after** checking Task 3 does not import them (Task 3 builds its own chart component under `components/artifacts/`).

**Do not touch:** `web/src/types.ts`, `web/src/api/index.ts`, anything under `web/src/components/artifacts/` (import `ArtifactView` from `components/artifacts/ArtifactView`; it is a stub that Task 3 replaces).

Behaviour: everything under "Frontend changes" in the spec except the artifact renderers. `http.ts`: `createHttpApi(baseUrl = '')`; maps 422 to `ValidationError`, 404 on `getMission` to `undefined`; `subscribe` starts a single shared 2s poll while there is at least one listener, stops when there are none, and notifies only when the JSON of the last `listMissions` + any watched mission changed (keep it simple: notify on every tick is acceptable if change detection gets complicated, but never leak timers). `mock.ts` is rewritten to the new model for tests and keeps the deterministic timer-driven progression (working → events accumulate → waiting with a conclusion); `sendMessage` appends a `user_message`, returns to `working`, then a scripted reply; `markDone` sets `done`. Sidebar groups are "Active" and "Done"; done rows are muted. Mission page: header (StatusDot, title, status text "Devin is working" / "Waiting for you" / "Done" / "Failed", "Open in Devin" external link only when `sessionUrl`, "Mark done" outline button hidden when done), event list, reply composer pinned to the bottom of the thread column (Enter sends, Shift+Enter newline, blank ignored, no double-send, disabled look while sending; replying to a done mission is allowed and reopens it). When `needsUser` is set show it as a quiet callout above the composer. Auto-scroll to new events only if the user is already within 80px of the bottom. When status is `done`, fold everything before the conclusion behind a single "Show the work" toggle (collapsed by default); if there is no conclusion, show all events. "Demo mode" note in the sidebar footer when `meta.demo`. New mission page: unchanged UX; after create navigate to the mission.

Verification to report: `npx vitest run` on all files you own, `npx tsc -b` filtered to errors in files you own, `npx oxlint` on your files.

### Task 3 (agent: web-artifacts): artifact renderers

**Files (owned):** everything under `web/src/components/artifacts/` — `ArtifactView.tsx` (replace the stub: a hairline card frame with title, optional headline in `font-mono` on the right, body, optional muted caption; switches on `artifact.type`; unknown type → `null`), `ChartArtifact.tsx` (Recharts line/scatter/bar in the existing chart idiom: 1.5px strokes, first series ink, second `#BDBDBD`, further series progressively fainter grays, hairline axis, 11px mono muted ticks, hairline tooltip, no grid, numeric or string x; lazy-load the Recharts-dependent part with `React.lazy` so the main bundle stays small, as `ResultCard.tsx` does today), `ImagesArtifact.tsx` (responsive grid, 4 across desktop / 2 on phones, 6px radius, `bg-fill` placeholder while loading, broken images collapse to a muted "Image unavailable" tile, captions 11px muted, `loading="lazy"`, `alt` from caption), `RelationArtifact.tsx` (pure SVG/HTML node-link diagram: layered left-to-right layout computed from edges with a small deterministic algorithm, pill nodes with 1px ink border, gray 1px edges with optional mono 11px labels, handles cycles, disconnected nodes, and edges that reference unknown node ids without crashing; horizontally scrollable on phones rather than overflowing), `TableArtifact.tsx` (hairline table, first column ink, numeric-looking cells right-aligned mono), `StatsArtifact.tsx` (the label/value grid from today's `StatRow`), `ImageArtifact.tsx`, plus a test file per component and `ArtifactView.test.tsx`.

**Do not touch** anything outside that folder. You may read `web/src/components/{SeriesChart,ResultCard,StatRow}.tsx` for the visual idiom but must not import them (they are being deleted).

Also create `web/src/components/artifacts/Gallery.tsx`: a dev-only page component rendering one realistic example of every artifact type stacked in a 720px column, exported as `ArtifactGallery`, so the lead can mount it temporarily and look at it. Verify visually yourself: temporarily render `ArtifactGallery` from `web/src/App.tsx` behind a `/__artifacts` route, run `npx vite --port 5181 --strictPort`, screenshot with headless Chrome at 1280 and via a narrow window, LOOK at the screenshots with the Read tool, fix ugliness, then **revert your `App.tsx` change** and kill the server. Keep screenshots outside the repo and report their paths.

Verification to report: `npx vitest run src/components/artifacts`, `npx oxlint src/components/artifacts`, tsc errors limited to your folder.

### Task 4 (lead): integrate

- [ ] Review each agent's diff; run the full gates: `npm test`, `npm run build`, `npx oxlint` in `web/`; `.venv/bin/python -m pytest -q`.
- [ ] Run server (demo mode) + web together; walk create → live thread → reply → mark done → reopen in the browser at desktop and phone widths.
- [ ] Run the live smoke test once (`pytest -m live`, ≤ 1 ACU); correct the v3 status/message mapping from what it prints; then run one real mission end to end from the UI.
- [ ] Update `README.md` (Web section: two processes, demo mode, `.env` key, ACU cap and mode env vars) and `AGENT.md`.
- [ ] Commit in logical pieces. Do not push or merge.

---

## Addendum: final report and dark mode

Approved mockup: a report is its own page, typeset like a short paper — eyebrow ("Mission report · date"), a large headline that states the finding, a one-paragraph summary, a row of key numbers, the featured artifacts re-rendered with the normal artifact components, "How we got there" as a numbered list (label in ink, takeaway muted), caveats and "Ask next" side by side, and a quiet footer with the castle mark. Header actions: "Back to mission", "Copy link", "Regenerate" (outline), "Export PDF" (the one ink button; uses `window.print()` with a print stylesheet).

### Contract (frozen; `web/src/types.ts` and `web/src/api/index.ts` are already updated)

```
POST /api/missions/:id/report   -> 202 {}
```

- Requesting a report sends Devin one message (`REPORT_REQUEST` in `server/brief.py`) in the mission's existing session, sets `reportPending: true`, and sets status `working` so the poller follows it. It adds **no** `user_message` event. A request while one is pending is a no-op 202. A mission with no session gets an `error` event and stays as it is (202, same pattern as replies). Devin unreachable: `error` event, `reportPending` stays false.
- If the mission was `done` when the report was requested it returns to `done` when the report arrives (or the request fails); otherwise it goes to `waiting` as usual.
- Devin answers by filling `report` in `structured_output` (snake_case): `{headline, summary, stats: [{label, value}] (≤ 4), key_artifact_ids: [..] (≤ 3, must be ids of artifacts it already emitted), steps: [{label, takeaway}] (≤ 8), caveats: [..] (≤ 4), next_questions: [..] (≤ 3)}`. The server validates and normalises to the camelCase `Report` in `types.ts`, drops unknown artifact ids, truncates over-limit lists, and requires non-empty `headline` and `summary` (otherwise it keeps waiting).
- A report counts as delivered when one is pending and the normalised content differs from the stored report (or none is stored). If a request has been pending for more than 5 minutes: accept an unchanged valid report if present, else add an `error` event ("The report did not arrive") and clear pending.
- On delivery: store the report with `generatedAt = now`, clear pending, and upsert the single `{kind: "report"}` event (id `report`) at the end of the thread, after the conclusion. While a report is not pending, a `report` in Devin's output is ignored.
- `GET /api/missions/:id` always includes `reportPending` (bool) and includes `report` only when one exists. Summaries are unchanged.
- The brief's standing text must tell Devin about the `report` field but also that it must leave it null until asked.
