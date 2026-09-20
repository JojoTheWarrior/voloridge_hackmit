# Steps Taken

## Probe and design

The initial probe in `/home/ubuntu/probe_notes.md` established the practical
shape of each source:

- OpenAQ's API returns 401 without a key and retired endpoints return 410.
  Anonymous S3 listing works, but a complete location scan is large.
- NOAA ISD metadata reaches 2025 but has no dependable 2026 inventory, so
  Open-Meteo supplies the current weather window.
- OpenAlex's unauthenticated API is subject to a paid per-IP budget. The
  parquet tree is the useful sampling path.
- Materials Project snapshots have document dates and snapshot dates, not a
  regular daily measurement series.
- PUDL provides the EIA demand, generation, fuel receipts, and generator
  changelog tables used here.
- The old GDELT S3 inventory is stale; live v2 HTTP exports are current.
- Finance symbols were checked through Yahoo Finance, with FRED as a fallback
  for Brent.

## Implementation chronology

1. Added configuration, manifests, fetchers, and smoke tests for GDELT, NOAA,
   Open-Meteo, OpenAQ, OpenAlex, Materials Project, PUDL, and finance.
2. Added the indicator registry, cached loaders, statistical transforms,
   alignment, lag correlations, circular permutation tests, event studies, and
   pre/post comparisons.
3. Added OpenAI and Jev clients, planner validation, mission reports, the
   lock-safe result CSV, queue harness, and CLI.
4. Fixed OpenAI's `max_completion_tokens` requirement, GDELT date-column
   handling and daily aggregation, heuristic score scaling, same-source
   planner selection, and FRED's `observation_date` column.
5. Added the Pygame VizSpec renderer, visualization agent, and Flask UI.
6. Refetched Open-Meteo's full 2025-03-01 through archive-latency range for all
   19 cities. Fixed cached GDELT clipping, planner city validation, OpenAQ
   downloaded-row registration, utility warnings, and Materials CSV loading.
7. Added shared JSON serialization, UI mission persistence and result browsing,
   documentation, and the current UI polish.
8. Corrected fixed-width NOAA ISD parsing (date, wind, visibility, signed
   temperature, and missing-value fields), added coverage-aware catalogue
   entries, and verified Tehran records against Open-Meteo.
9. Added the no-key Open-Meteo Air Quality/CAMS fetcher with 90-day chunks and
   eight daily indicators per city. A full refresh produced 13,584 hourly
   values / 566 daily means per city through archive latency.
10. Made OpenAQ registration parameter-aware, restricted event markers from the
    planner catalogue, tightened multi-city validation and heuristic fallback,
    and added one heuristic retry for insufficient-overlap queue missions.
11. Added a resumable no-key Crossref REST fetcher for 20 topics plus an
    all-works control, with weekly publication counts and per-10k shares.
    Sparse OpenAlex and static Materials Project series are retained for
    callable context but removed from planner catalogue selection.
12. Preserved weekly alignment and made lag units explicit (`days`, `weeks`,
    or `months`) in reports and visualizations.
13. Added Devin child-session brain integration with OpenAI and heuristic
    fallbacks. Planner, narrative, and visualization calls retain backend
    metadata in run manifests and result indexes.

## Download snapshot

Recompute with `du -sh data/raw/*`. At the latest inspection:

```text
finance           1.2M
gdelt_live         14G
materials_project 138M
noaa_isd           7.3M
open_meteo         564K
open_meteo_aq      17M
crossref           weekly topic JSON and manifest
openalex           88M
openaq             61M
pudl               373M
```

These sizes are working-cache snapshots, not source guarantees. Raw data and
reports are intentionally ignored by Git.

## Commands used

```bash
python -m warsignal.fetch.open_meteo --start 2025-03-01 --end 2026-09-15
python -m warsignal.fetch.crossref --start 2025-03-03
python main.py fetch --quick
python main.py selftest
python -m pytest -q tests
python main.py mission "..." --viz
python main.py queue --n 5
python main.py ui --port 8000
```

The source-specific fetch commands and credentials are documented in
`AGENT.md`.

## Bugs found during development

- GPT-5.x rejects `max_tokens`; requests now use `max_completion_tokens` and
  retry a truncated response with a larger budget.
- GDELT v1 dates come from the data row's date column, not the filename.
- Open-Meteo quick-range files must be refetched when their date bounds do not
  cover the requested full window.
- Heuristic judge interestingness and unexpectedness must use the 0–10 scale.
- The planner must choose distinct sources for explicitly different domains
  whenever a positive-scoring alternative exists.
- FRED exports can use `observation_date` rather than `DATE`.
- Indicator caches need safe existence checks and stale GDELT clipping.
- Queue missions exposed sparse overlap and city substitution errors; runners
  now report coverage and planner validation errors clearly.
- NOAA ISD is a short historical station source (`2025-03..2025-08`), while
  CAMS model data extends the air-quality window but must not be described as
  ground-sensor observations.
- OpenAlex's sampled parquet and Materials Project snapshots are too sparse or
  static for dense research timing; Crossref weekly totals are the preferred
  no-key publication source.

## Timeline and known failures

The event reference is `data/reference/iran_timeline.csv`, with date,
category, event, description, market note, and source URL columns.

Known limitations include missing Tehran OpenAQ rows, uneven OpenAQ archive
coverage, sparse GDELT windows for some old reports, NOAA's 2026 inventory
gap, and the fact that a significant correlation can still be seasonal,
confounded, or caused by the shared war shock. A mission with fewer than 20
overlapping observations fails rather than presenting unstable statistics.

## Next actions

- Finish the 100-mission queue run and review failure causes.
- Validate the strongest hypotheses against independent data windows.
- Replace placeholder insights with evidence-backed findings.
- Add source-specific freshness checks and richer provenance to reports.

## Insights

(filled after the 100-mission run)
