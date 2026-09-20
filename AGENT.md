# WarSignal Agent Guide

## Environment and credentials

Create `.env` from `.env.example`. Supported secrets include:

- `OPENAI_API_KEY`: planner, narrative, and OpenAI judge fallback.
- `TYPESAFE_API_KEY`: Jev/System One (`console.typesafe.ai`).
- `OPENAQ_API_KEY`: optional API discovery; the anonymous S3 archive is used
  for the long scan when possible.
- `OPENALEX_API_KEY`: optional API count queries; parquet sampling is primary.

Never print, commit, or include secret values in reports or logs.

## Fetch workflows

Use the quick orchestrator for a smoke-sized refresh:

```bash
python main.py fetch --quick
```

Use the full orchestrator when storage and time permit:

```bash
python main.py fetch --all
```

Useful direct commands:

```bash
python -m warsignal.fetch.open_meteo --start 2025-03-01 --end 2026-09-15
python -m warsignal.fetch.open_meteo_aq --start 2025-03-01 --end 2026-09-17
python -m warsignal.fetch.crossref --start 2025-03-03
python3 -m warsignal.fetch.openaq --max-ids 4000
python3 -m warsignal.fetch.openaq --max-ids 60000
python -m warsignal.fetch.gdelt --start 2025-03-01 --end 2026-09-19
python -m warsignal.fetch.finance --start 2025-01-01 --end 2026-09-19
```

The working raw-data sizes have been approximately finance 1.2M, GDELT 14G,
Materials 138M, NOAA 7.3M, Open-Meteo 564K, CAMS 17M, OpenAlex 88M,
OpenAQ 61M, and PUDL 373M. Recompute with `du -sh data/raw/*`; sizes change
as scans run.

OpenAQ scans are long-running and should be chained rather than duplicated.
Open-Meteo archive data has roughly five days of latency. NOAA ISD currently
ends before the configured current window. OpenAlex's API can reject
unauthenticated requests because its budget is paid; use the S3 parquet sample.
Materials snapshots are document metadata, not a daily observation stream.
Open-Meteo Air Quality supplies keyless CAMS model reanalysis for all
configured cities; it is separate from OpenAQ ground sensors. NOAA ISD
indicators are explicitly limited to `2025-03..2025-08`, and catalogue entries
expose static or cache-derived coverage.
Crossref fetches weekly query totals and a no-query control series; it is
resumable per topic under `data/raw/crossref/` and requires no key. OpenAlex
is retained for callable sparse context only, while Materials Project remains
static context rather than a publication-time series.

## Adding an indicator

Add a module under `warsignal/indicators/`, import it in
`warsignal/indicators/__init__.py`, and register a loader:

```python
from warsignal.indicators.base import IndicatorSpec, register

register(
    IndicatorSpec(
        name="example.signal",
        source="research",
        description="A daily example signal",
        unit="count",
        freq="D",
        region=None,
    ),
    lambda: load_example_series(),
)
```

The CAMS registrations are `airquality.<city>.cams_pm25`,
`cams_pm10`, `cams_no2`, `cams_so2`, `cams_o3`, `cams_co`, `cams_dust`, and
`cams_aod`. OpenAQ ground indicators are registered only for parameters found
in downloaded rows for the matched city; inspect
`data/cache/openaq_city_params.json` when diagnosing availability.

Loaders should return a float `pandas.Series` with a sorted, unique,
timezone-naive `DatetimeIndex`. `get_series()` handles the 24-hour indicator
cache and raises `IndicatorUnavailable` for missing raw data.

## Running missions and queues

```bash
python main.py mission "Iran news volume leads Brent returns" --viz
python main.py mission "..." --dry-run
python main.py queue --n 5
python main.py queue --n 5 --viz
python main.py queue --n 5 --max-retries 1
python main.py queue --reset
python main.py queue --requeue-failed
```

## Mission protocol

`python main.py mission "..."` writes a numbered, self-contained run under
`missions/runs/` and updates `missions/runs/INDEX.md`; queue missions do the
same. Each run contains `hypothesis.txt`, `plan.json`, `stats.json`,
`judge.json`, `note.md`, raw and aligned CSV data, and a manifest. Add
`--publish` to `mission` or `queue` to commit only that run and the index, then
push. Publishing is disabled by default; failed publish pushes are logged and
do not fail the mission.

The queue atomically moves a line into `missions/in_progress.txt`, appends a
result under a file lock, then marks it done or failed. Do not edit
`queue.txt`, `results.csv`, or `in_progress.txt` while another queue process is
running. `--reset` restores `queue_original.txt` and clears in-progress work;
it does not alter results.

## Mission pipeline

The planner returns the JSON contract represented by `MissionPlan`:
indicator names, transforms, lag limit, window, event category, null-control
flag, expected sign, and rationale. AI plans are checked against the registry,
for duplicate indicators, and for requested-city/source mismatches. A
single-series plan may repeat the same indicator (or set `mode` to `single`)
for a pre/post or event-category change; it writes one raw series and reports
pre/post means, Welch p, and effect size instead of correlation and lag fields.
The
heuristic planner uses catalogue keyword overlap and prefers different sources
for different domains.

The runner loads both series, applies `level`, `diff`, `pct_change`,
`log_return`, `zscore`, or `anomaly`, then aligns dates. It can restrict to
the full sample, war window, or pre/post comparison. Results include Pearson
and Spearman correlations, lagged correlations, circular-shift permutation
probability, a Bonferroni adjustment for tested lags, optional event studies,
and pre/post Fisher-z comparison. Fewer than 20 overlapping observations is a
clean failure.

Judging follows Jev → OpenAI `gpt-5-mini` fallback → deterministic heuristic.
The heuristic considers sample size, permutation probability, effect size,
source diversity, lag stability, pre/post change, sign mismatch, and null
controls. Every score is 0–10; supported probability is 0–1.

CSV columns include mission identity/status, hypothesis and plan fields,
source/date coverage, `n_obs`, overall and lagged statistics, permutation and
Bonferroni probabilities, event/pre-post fields, judge scores, planner/judge
metadata, summary, report path, visualization path, and error.

## UI and Pygame visualization

```bash
python main.py ui --port 8000
python main.py viz M20260920-abcdef --headless
python main.py viz M20260920-abcdef
```

The UI runs missions synchronously, appends them to `missions/results.csv`,
shows reports and PNGs, and can launch the interactive viewer. The viewer
supports hover values, wheel zoom, drag pan, `N` normalization, `E` event
markers, `S` screenshot, numeric series toggles, and `Q`/Escape to quit.

## Statistical hygiene

Correlation is not causation. Report `n`, date coverage, missingness, lag
selection, multiple-testing adjustment, and the possibility that the war is a
common cause. Do not fill missing returns forward, do not infer a relationship
from a handful of overlapping dates, and treat event categories and curated
timeline dates as hypotheses rather than ground truth.

## Lessons learned

Use `max_completion_tokens` with GPT-5.x, inspect real schemas before writing
parquet selectors, validate date columns instead of trusting filenames, keep
heuristic scores on their documented scale, preserve requested city identity,
and make every boundary crossing JSON-safe. Long-running scans and queues are
shared state: check processes first and never restart or reset them casually.
