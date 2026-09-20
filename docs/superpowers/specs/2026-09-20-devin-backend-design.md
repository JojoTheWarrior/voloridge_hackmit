# Live missions with Devin — design

Date: 2026-09-20

## Goal

Make missions real. Starting a mission in the web app creates a Devin session
that does the research; the app shows Devin's thinking, steps, and visual
artifacts as they happen; the user can reply like a chat and marks the mission
done when satisfied. Builds on `2026-09-20-web-frontend-design.md`; the visual
rules there still apply.

## Decisions already made

- Devin is a **free-form researcher**: it gets the hypothesis and the linked
  dataset URLs, fetches data, writes its own analysis, and reasons in the open.
  It does not run the fixed `warsignal` pipeline.
- Missions may carry a **reference** (prior research to retrace). Devin uses
  it privately as a map and presents the work as its own natural
  investigation, never mentioning the reference. The data model and prompt
  support it now; the import UI is phase 2.
- **Artifacts** are visuals along the way, chosen intelligently by Devin from a
  typed vocabulary and rendered by the app in its own style.
- **Done is the user's call.** Devin finishing a turn does not end a mission.
- The Devin key in use is a v3 service-user key (`cog_…`). v1 rejects it, so
  the backend uses the **v3 API**; `warsignal/ai/devin_client.py` (v1) is left
  untouched for the existing CLI.

## Architecture

```
web (React)  ──HTTP /api──▶  server (Flask)  ──v3 REST──▶  Devin
   polls every 2s               SQLite file
                                poller thread (syncs live missions every 5s)
```

New top-level `server/` package, started with `python main.py serve
[--port 8030]`. Vite proxies `/api` to it in dev. No auth (binds to
127.0.0.1, same stance as the old terminal).

```
server/
  app.py          Flask app factory + routes
  store.py        SQLite persistence (missions, events, datasets)
  devin.py        DevinClient protocol, V3DevinClient, FakeDevin
  sync.py         turn a Devin session snapshot into new mission events
  poller.py       background thread: sync every live mission
  brief.py        builds the research prompt + structured-output schema
  artifacts.py    validate/normalise artifact specs from Devin
tests/server/     pytest, one file per module
```

Each unit has one job: `devin.py` knows HTTP and nothing about missions;
`sync.py` is a pure function from (stored state, Devin snapshot) to new events,
so it is tested without network or threads; `poller.py` only schedules.

### Devin client

```python
class DevinClient(Protocol):
    def create_session(self, prompt, *, title, schema, max_acu) -> SessionRef
    def get_session(self, session_id) -> SessionSnapshot   # status, structured_output, acus
    def list_messages(self, session_id) -> list[DevinMessage]
    def send_message(self, session_id, text) -> None
    def list_attachments(self, session_id) -> list[Attachment]
```

`V3DevinClient` resolves the org id once from `GET /v3/self`, then uses
`/v3/organizations/{org}/sessions[/{id}[/messages|/attachments]]`. Retries
once on 429/5xx; raises `DevinUnavailable` otherwise. Sessions are created with
`max_acu_limit` (default 5, `KINGDOM_MAX_ACU`), `devin_mode` (default `fast`,
`KINGDOM_DEVIN_MODE`), and tag-free titles `Kingdom: <mission title>`.

`FakeDevin` implements the same protocol in memory with a scripted research
run (thoughts, steps, and one of every artifact type, then waits; replies get a
scripted answer). The server uses it when `DEVIN_API_KEY` is unset or
`KINGDOM_FAKE_DEVIN=1`, so the app works out of the box with no key and tests
never spend ACUs. The UI shows a small "Demo mode" note in the sidebar footer
when the fake is active (`GET /api/meta`).

### The brief (how Devin is told to behave)

`brief.py` builds one prompt from: the hypothesis, the selected datasets
(name + URL), the optional reference, and standing instructions:

- You are a research analyst. Think out loud: post a short message whenever you
  learn something, change your mind, or hit a problem. Plain prose, no
  markdown headers, first person.
- Keep `structured_output` current after every meaningful step. It is the
  source of truth for steps, artifacts, and the conclusion.
- Emit an artifact whenever something is better seen than read: what the data
  looks like (image samples for visual datasets), how datasets relate or join,
  distributions, the key comparison, robustness checks. Choose the type that
  fits; use `image` with an attachment only when no typed artifact can express
  it.
- Always report the core stats when testing a relationship: effect/correlation,
  lag, p-value, n, and what would falsify it. A null result is a valid result.
- When you have a conclusion, or need a decision from the user, say so and
  wait. Do not end the session yourself.
- With a reference: treat it as private notes on where to look. Retrace that
  line of inquiry as your own investigation, in your own words, in the same
  order of ideas, and never mention, quote, or allude to a reference, prior
  work, or replication. Actually run every analysis and report what the data
  shows. Never adjust, invent, or select results to match the reference; if the
  data leads somewhere else, follow the data and conclude that instead.

Structured-output schema (validated server-side; unknown fields dropped):

```json
{
  "steps":     [{"id": "s1", "label": "Read both datasets", "state": "done|active"}],
  "artifacts": [{"id": "a1", "after_step": "s1", "type": "...", "title": "...", "caption": "...", ...}],
  "conclusion": {"verdict": "...", "summary": "...", "stats": [{"label": "...", "value": "..."}]} | null,
  "needs_user": "question for the user, or null"
}
```

Artifact types and their payloads:

| type | payload |
| --- | --- |
| `chart` | `kind: line\|scatter\|bar`, `x_label`, `y_label`, `series: [{name, points: [[x, y], ...]}]` (≤ 2 series emphasised ink/gray, ≤ 500 points each), optional `headline` e.g. `r = 0.58` |
| `images` | `items: [{src, caption}]` (≤ 8); `src` is an https URL or `attachment:<name>` |
| `relation` | `nodes: [{id, label}]`, `edges: [{from, to, label}]` (≤ 12 nodes) |
| `table` | `columns: [..]`, `rows: [[..]]` (≤ 10 rows, ≤ 6 columns) |
| `stats` | `items: [{label, value}]` (≤ 6) |
| `image` | `src`, fallback for anything else |

Invalid artifacts are skipped and logged, never crash a sync. Over-limit
payloads are truncated. `attachment:<name>` is resolved against the session's
attachment list and served through `GET /api/missions/<id>/attachments/<name>`
(server-side fetch, so the browser never needs Devin credentials; only
image content types are proxied).

### Mission model and lifecycle

```
status:  working | waiting | done | failed
```

- `working` — Devin session is running.
- `waiting` — Devin is idle: it asked something (`needs_user`), posted a
  conclusion, or the session is blocked/suspended awaiting input.
- `done` — the user clicked "Mark done". Polling stops. Replying reopens it
  (status returns to `working`).
- `failed` — session errored, expired, hit the ACU cap, or Devin was
  unreachable at creation. The error is shown; the mission can be marked done
  to clear it from the active list.

A mission's thread is an ordered list of **events**, persisted in SQLite:

| kind | fields |
| --- | --- |
| `user_message` | text |
| `thought` | text (a Devin message) |
| `step` | step id, label, state |
| `artifact` | the validated artifact spec |
| `conclusion` | verdict, summary, stats |
| `error` | text |

`sync.py` diffs each snapshot against what is stored: new Devin messages become
`thought` events (the echo of our own user messages is skipped); new or changed
steps upsert `step` events; new artifacts append `artifact` events placed after
their `after_step`; a changed conclusion replaces the `conclusion` event.
Syncing the same snapshot twice produces nothing new (idempotent).

### HTTP API

```
GET    /api/meta                         {demo: bool, max_acu, devin_mode}
GET    /api/missions                     summaries, newest first
POST   /api/missions                     {hypothesis, datasetIds, reference?} -> mission
GET    /api/missions/:id                 mission + events
POST   /api/missions/:id/messages        {text} -> 202; reopens a done mission
POST   /api/missions/:id/done            marks done
GET    /api/missions/:id/attachments/:n  proxied image
GET    /api/datasets                     list
POST   /api/datasets                     {name, url} -> dataset
```

Validation errors return `422 {field, message}`, matching the frontend's
existing `ValidationError`. Devin being unreachable on create returns the
mission with `status: failed` and an `error` event rather than a 5xx, so the
user sees what happened in the thread.

Datasets are seeded with the four existing sources on first run.

## Frontend changes

- `types.ts`: `MissionStatus` becomes `working | waiting | done | failed`;
  `Mission` gains `events: MissionEvent[]`, `sessionUrl`, and drops
  `steps`/`result`. `MissionEvent` and `Artifact` are discriminated unions
  mirroring the tables above.
- `api/index.ts`: add `sendMessage(id, text)`, `markDone(id)`, `getMeta()`;
  `createMission` accepts optional `reference`.
- `api/http.ts`: fetch-based `Api`; `subscribe` is driven by a 2s poll that
  only notifies when the payload changed. `main.tsx` uses it by default.
- `api/mock.ts` is kept, rewritten to the new model, and used only by tests.
- Sidebar: groups become **Active** (working, waiting, failed) and **Done**
  (greyed). Status dots: filled = working, half-filled = waiting for you,
  hollow = done, crossed = failed. "Demo mode" note when `meta.demo`.
- Mission page becomes the thread from the approved mockup: a slim header
  (dot, title, status text, "Open in Devin" link, "Mark done" outline button),
  events rendered in order — thoughts as plain prose, steps as quiet markers
  (spinner on the active one), artifacts as hairline cards, the conclusion as
  the final card with verdict and stat row — and a reply composer pinned to the
  bottom. Auto-scrolls to new events only when already at the bottom.
- Artifact renderers, one component each: `ChartArtifact` (extends the
  existing Recharts styling to scatter and bar), `ImagesArtifact`,
  `RelationArtifact` (simple layered SVG layout, ink nodes, gray edges),
  `TableArtifact`, `StatsArtifact`, `ImageArtifact`. Unknown types render
  nothing.
- The old step-collapse ("Worked for 4m") applies once a mission is done:
  thoughts and steps before the conclusion fold behind one line.

## Error handling

- Devin 429/5xx while polling: keep the mission `working`, retry next tick,
  surface nothing until 5 consecutive failures, then add one `error` event
  ("Lost contact with Devin, still retrying").
- Session `error`/expired: `failed` + `error` event with Devin's detail.
- Malformed structured output: ignored for that tick; messages still sync.
- Server restart: the poller reloads all `working`/`waiting` missions from
  SQLite and resumes.
- Frontend fetch failure: the thread keeps its last state and shows a quiet
  "Reconnecting" line in the header.

## Testing

- `sync.py`: table-driven tests — first sync, idempotent re-sync, new message,
  own-message echo skipped, step state change, artifact ordering by
  `after_step`, conclusion replaced, needs_user → waiting, each terminal
  session status → failed, malformed output ignored.
- `artifacts.py`: every type valid/invalid, truncation limits, attachment refs.
- `devin.py`: `V3DevinClient` against a stubbed `requests` (URLs, headers,
  retry-once, error mapping, org id cached); `FakeDevin` script progression.
- `store.py`: round-trips, ordering, reopen, restart reload.
- `app.py`: every route, 422 shapes, create-with-Devin-down, attachment proxy
  refuses non-image content and unknown names.
- Frontend: the existing suites updated to the new model, plus each artifact
  renderer, the reply composer (Enter/Shift+Enter/blank/double-send), mark
  done → moves to Done and greys, reply reopens, demo note, auto-scroll rule.
- One **live smoke test**, run manually and excluded from the default suite
  (`pytest -m live`): creates a real session with a tiny prompt and
  `max_acu_limit: 1`, checks a message and structured output arrive, then
  stops. Run once to confirm the v3 field names the docs leave unspecified
  (message shape, status values), and fix the client if they differ.

## Out of scope (next)

Phase 2: replication import (build a `reference` from a `missions/runs/`
folder or pasted markdown; a "Replicate" entry point in the UI). Dataset
ingestion/preview and real thumbnails. Auth, multi-user, deploying the server.
