# WarSignal

WarSignal is an alternative-data hypothesis lab for the Voloridge HackMIT
“Signal in the Noise” challenge. It combines public news, weather, air
quality, research, materials, energy, events, and market data into registered
indicators, then tests hypotheses with aligned correlations, lag searches,
permutation tests, event studies, and pre/post comparisons. Every mission
leaves a JSON/Markdown report and can produce an interactive Pygame chart.

## Quickstart (60 seconds)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py fetch --quick
python main.py mission "Iran news volume leads Brent crude returns" --viz
python main.py ui
python main.py queue --n 5
```

### Brain backends

WarSignal uses Devin child sessions as the default brain for planner
reasoning, narrative notes, and visualization design/code generation. Put
`DEVIN_API_KEY` in `.env`, then find the mission sessions at
`https://app.devin.ai` by filtering for the `warsignal` tag. Each session is
also tagged with its purpose and mission ID. If Devin is unavailable, WarSignal
logs the fallback and uses OpenAI; select a backend explicitly with
`--brain devin`, `--brain openai`, or `--brain heuristic` on `mission` and
`queue`. The heuristic option disables LLM calls.

### Run a mission as a Devin agent

Use `--detach` to create one Devin child session and return immediately; the
child clones the repository, runs the mission, updates `missions/status/`, and
publishes its run folder:

```bash
python main.py mission "Iran news leads Brent returns" --detach
python main.py queue --detach --n 5
```

The local queued status file is written atomically and is intentionally left
uncommitted for the child agent. File locking works on both POSIX and Windows.

### Mission protocol

Every mission writes a self-contained, reproducible folder under
`missions/runs/` containing its hypothesis, plan, statistics, judge response,
aligned/raw data, narrative, manifest, and (when requested) `viz.png`.
`missions/runs/INDEX.md` is regenerated after each mission. Use
`--publish` with `mission` or `queue` to commit the run folder and index and
push them to the current branch; publishing is off by default.

Network fetches are optional after raw data and indicator caches exist. Never
commit `.env`, downloaded data, reports, or mission result CSVs.

## Entrypoint

| Command | Purpose |
| --- | --- |
| `python main.py fetch --quick` / `--all` | Fetch configured public datasets |
| `python main.py indicators [--source X]` | List the indicator catalogue |
| `python main.py mission "..." [--no-ai] [--brain X] [--dry-run] [--viz] [--show]` | Plan or run one mission |
| `python main.py mission "R2 \| ..." --mission-id R2-0001 --status --publish` | Round 2: run one mission and keep `missions/status/R2-0001.json` updated |
| `python main.py status R2-0001 [--state S] [--stage S] [--followup "R2 \| ..."] [--push]` | Round 2: update a mission status file / append a follow-up |
| `python main.py queue [--n N] [--no-ai] [--brain X] [--viz]` | Run queued hypotheses |
| `python main.py queue --reset` | Restore `missions/queue.txt` from its backup |
| `python main.py queue --requeue-failed` | Put failed hypotheses back in the queue |
| `python main.py viz M... [--headless]` | Render a mission visualization |
| `python main.py ui [--port 8000]` | Start the Flask hypothesis interface |
| `python main.py graph [--port 8010] [--charts-port 8011]` | NL prompt → pygame chart web UI + launcher |
| `python main.py selftest` | Check keys, judge availability, and indicator loading |
| `python main.py serve [--port 8030] [--db PATH]` | API server for the web UI; creates and polls Devin sessions (see [Web](#web)) |
| `python main.py kingdom [--scale N] [--scene S] [--screenshot out.png]` | Pixel-art mission dashboard (see [Kingdom](#kingdom)) |

## Web

Kingdom's product UI: link datasets, start a mission, and watch Devin research
it live — its thinking as prose, its steps, and visual artifacts (charts, image
samples, join diagrams, tables, stats) as they are produced. Reply to steer it
like a chat, and mark the mission done when you are satisfied.

Two processes. Needs Node 20.19+ or 22.12+ (`node -v`) and the repo's Python
environment:

```bash
python main.py serve                 # API + Devin poller on http://127.0.0.1:8030
cd web && npm install && npm run dev # UI on http://localhost:5173 (proxies /api to 8030)
```

**Demo mode (no key needed).** With no `DEVIN_API_KEY`, or with
`KINGDOM_FAKE_DEVIN=1`, the server runs a scripted fake Devin that plays a full
research run with one artifact of every type, so everything works out of the
box and nothing is spent. The sidebar shows "Demo mode".

**Live mode.** Put a Devin **v3 service-user key** (`cog_…`) in `.env` as
`DEVIN_API_KEY` (the file is gitignored; never commit it). Each mission creates
one Devin session. Spend is capped per mission:

| Variable | Default | Meaning |
| --- | --- | --- |
| `KINGDOM_MAX_ACU` | `5` | `max_acu_limit` for each session |
| `KINGDOM_DEVIN_MODE` | `fast` | Devin mode: `lite`, `fast`, `normal`, … |
| `KINGDOM_FAKE_DEVIN` | unset | `1` forces demo mode even with a key |

Missions and their threads persist in `.kingdom/kingdom.db` (SQLite,
gitignored), so a restart resumes polling live missions.

How it fits together: `server/brief.py` writes Devin's instructions and the
structured-output schema; `server/devin.py` is the v3 client (and the fake);
`server/sync.py` is a pure function that turns each Devin snapshot into ordered
thread events; `server/poller.py` runs it for every live mission;
`server/app.py` serves the JSON the UI reads. The UI only knows the `Api`
interface in `web/src/api/index.ts`; `http.ts` implements it, and `mock.ts` is
an in-memory twin used by the tests.

```bash
python -m pytest tests/server -q          # server tests, fully offline
python -m pytest tests/server -m live -s  # one real Devin session, ≤ 1 ACU
cd web && npm test && npm run build       # UI tests, type-check, build
```

## Research

`research/` is a snapshot of the team's idea-by-idea research: every script,
the running verdicts in `research/IDEAS.md`, reports, `findings.json` files
for the frontend, result tables and figures. The data behind it (about 21 GB)
is not in the repo. See `research/README.md` for what each folder is, what was
left out, and how to refresh the snapshot.

## Iran Round 2 (tradeable rules)

Round 2 narrows the research to a tradeable universe (oil & tankers, gas/LNG,
fertilizer/ag, fuel/airspace losers, risk-macro/EM — all yfinance tickers in
`warsignal/fetch/finance.py`) and turns every mission into a rule. Hypotheses in
`missions/queue.txt` are prefixed `R2 |` and end with an explicit
`[signal_indicator -> target_indicator]` tag that the planner honours. Each run
adds `trade.json` + a `trade_idea` (entry rule, direction, holding days,
n_trades, hit rate, excess return vs baseline, Sharpe-like, drawdown, pre-war fit
vs war-period test) and an `actionability` score (0–10) to `results.csv`,
`manifest.json` and `missions/runs/INDEX.md`. See `missions/ROUND2_RUBRIC.md`
(the rule and score), `missions/ROUND2_AGENT_PROTOCOL.md` (what a mission child
does), `missions/status/SCHEMA.md` (progress files) and, when the round is done,
`missions/ROUND2_REPORT.md` (best five rules).

## Kingdom

Kingdom is a calm 8-bit pixel-art dashboard that turns the `missions/` folder
into a living fortress: one worker hut per active mission, a monument per
completed run, and a great hall with menus for current, queued, and completed
missions (click the castle or press Enter; Esc walks back out).

```bash
python main.py kingdom                      # windowed, 3x upscale of a 480x270 canvas
python main.py kingdom --scale 2 --scene completed
python main.py kingdom --screenshot kingdom.png   # headless render for CI/tests
pytest tests/test_kingdom_*.py -q
```

It is read-only, polls `missions/` every ~2 s, and disables audio. Details,
controls, and the asset pipeline live in `kingdom/README.md`.

## Architecture

```text
public sources
     │
     ▼
fetchers/raw manifests ──► indicators/register + cache
                                  │
                                  ▼
mission engine
  planner (gpt-5.1 or heuristic)
      └── stats (align, transforms, lags, permutations, events)
              └── judge (Jev → OpenAI fallback → heuristic)
                      └── narrative
                                  │
                                  ▼
             missions/results.csv + reports/*.json|*.md + viz/*.png
```

## Data sources

| Source | Coverage used | Limitation |
| --- | --- | --- |
| GDELT v1/v2 and GKG | Daily window from 2025-03 through current data | News volume and tone are proxies; source coverage changes |
| Open-Meteo | 19 cities, daily weather through archive latency | Forecast/archive revisions and seasonal confounding |
| NOAA ISD | 2025-03 through 2025-08 station observations | ISD-only series stop in 2025-08; station and field coverage vary |
| OpenAQ | Cities with indexed locations and downloaded rows | API requires a key; S3 archive coverage is uneven |
| Open-Meteo CAMS | 19 cities, 2025-03 through archive latency | Model reanalysis, not ground sensors; spatial smoothing and revisions |
| Crossref | Weekly publication counts/shares from 2025-03 through current week | Query totals are bibliographic matches, not full-text prevalence or causal output |
| OpenAlex | Sparse S3 sample (about 8 weekly observations) | Not suitable for dense time-series missions; prefer Crossref |
| Materials Project | Static document/materials snapshot | Not a daily research-timing series; use Crossref for publication timing |
| PUDL/EIA | Demand, generation, fuel, and generator tables | Publication and revision delays; regional aggregation choices |
| Yahoo Finance/FRED | Daily market prices and selected macro series | Trading calendars, symbol semantics, and vendor revisions |
| Iran timeline | Curated dates in `data/reference/iran_timeline.csv` | Event selection is curated and not exhaustive |

## Statistical caution

WarSignal reports associations, not causal effects. Always inspect sample size,
coverage, the common war shock, seasonal structure, multiple lag tests, and
plausible common causes before treating a result as evidence.

## Graph reels

`python main.py graph [--port 8010] [--charts-port 8011]` starts a small web UI
for natural-language charts and a `charts.py` pygame launcher window manager.

- Type a prompt ("the instagram reels of the price of brent"); the planner maps
  it to registered indicators (or external yfinance/FRED symbols when nothing
  fits), writes a `graphs/YYYYMMDD-NNN-<type>_<slugs>/` folder, renders
  `thumbnail.png`, commits the folder + `graphs/INDEX.md`, and pushes — each
  graph folder is a shareable, committed artifact.
- `chart.py` defaults to a deterministic reference template; the planner sets
  `needs_custom_code` only for requests outside reel/line/spread/scatter
  (histograms, dual-axis, candlesticks…), in which case gpt-5.1 adapts the
  template under strict "change as little as possible" rules with validator and
  render-repair fallbacks back to the template. `plan.json` records
  `codegen: template|llm|llm-repaired|template-fallback`.
- Chart types: `reel` (animated day-by-day playback), `line`, `spread`, and
  `scatter` (with OLS fit and `r=` readout).
- Reel controls: Space play/pause, ←/→ scrub (hold to repeat), ↑/↓ speed,
  Home/End, R restart, S screenshot, Q/Esc quit. Static charts support hover
  readouts, S, and Q.
- Repeat prompts reuse cached folders (fuzzy match ≥0.92 auto-hits; borderline
  matches are confirmed by gpt-5-mini). Cached charts with stale CSVs are
  refreshed before launch.
- Safety: generated `chart.py` is AST-validated — only pygame/pandas/numpy and
  stdlib modules are importable, no network/file-writing calls; renders happen
  in a subprocess via `charts.py`.
