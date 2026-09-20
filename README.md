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

Network fetches are optional after raw data and indicator caches exist. Never
commit `.env`, downloaded data, reports, or mission result CSVs.

## Entrypoint

| Command | Purpose |
| --- | --- |
| `python main.py fetch --quick` / `--all` | Fetch configured public datasets |
| `python main.py indicators [--source X]` | List the indicator catalogue |
| `python main.py mission "..." [--no-ai] [--dry-run] [--viz] [--show]` | Plan or run one mission |
| `python main.py queue [--n N] [--no-ai] [--viz]` | Run queued hypotheses |
| `python main.py queue --reset` | Restore `missions/queue.txt` from its backup |
| `python main.py queue --requeue-failed` | Put failed hypotheses back in the queue |
| `python main.py viz M... [--headless]` | Render a mission visualization |
| `python main.py ui [--port 8000]` | Start the Flask hypothesis interface |
| `python main.py graph [--port 8010] [--charts-port 8011]` | NL prompt → pygame chart web UI + launcher |
| `python main.py selftest` | Check keys, judge availability, and indicator loading |

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
| OpenAlex | Sampled recent parquet works | S3 sample is not the complete scholarly corpus |
| Materials Project | Document metadata snapshots through 2025 | Snapshots are not a daily scientific measurement series |
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
