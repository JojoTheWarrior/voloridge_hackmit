# Polymarket as a dataset (P2)

Start with [REPORT.md](REPORT.md), [results.csv](results.csv), and
[findings.json](findings.json). Figures are under `figures/`.

The 22 primary specifications and their timing rules are frozen in `prereg.json`;
`prereg.sha256` verifies the original bytes. The transport-only amendment allows
the official keyless, read-only batch-history endpoint. It does not change tests.

## Offline reproduction

Use the supplied `.venv` or build the folder's Dockerfile. From this folder:

```sh
.venv/bin/python stations.py
.venv/bin/python weather_panel.py
.venv/bin/python other_panel.py
.venv/bin/python baseline_panel.py
.venv/bin/python physical_panel.py
.venv/bin/python cross_venue.py
.venv/bin/python analyze.py
.venv/bin/python publish.py
.venv/bin/python validate.py --artifacts
```

`other_panel.py` and `physical_panel.py` initially read sibling public-data caches,
without modifying them. Their derived inputs are retained in this folder.
`physical_panel.py` can be skipped to reuse its already-built Parquet panel.

The report lists acquisition commands. Do not rerun the completed Gamma crawler
or `register.py`. All new HTTP responses, including errors, are cached on disk.
Acquisition uses one in-flight request per worker, a half-second pause and
exponential backoff for 429/5xx. The official batch endpoint reads at most 20
token histories per request and does not place orders or change accounts.

## Principal datasets

| File | Meaning |
|---|---|
| `data/weather_catalog.parquet` | Original 140,128-row catalogue, unchanged |
| `data/catalog_enriched.parquet` | Recovered ICAO query parameters and explicit IANA zones |
| `data/weather_sample_events.parquet` | Frozen deterministic 2,400-event sample |
| `data/prices/*.parquet` | Five-minute historical token samples |
| `data/station_daily.parquet` | Quality-screened local days, all-source and METAR subsets |
| `data/settlement_audit.parquet` | Every event's audit or exclusion reason |
| `data/weather_calibration.parquet` | As-of day-ahead market and baseline probabilities |
| `data/weather_crossings.parquet` | Threshold observations, assumed availability, price response |
| `data/other_daily.parquet` | Daily changes for non-weather missions |
| `data/baseline_calibration.parquet` | Exact scheduled-end minus 24-hour baseline panel |
| `data/flare_point_in_time.parquet` | 2026 FRP using a hotspot mask frozen in 2025 |
| `data/cross_venue_snapshot.parquet` | Descriptive snapshot, not identical historical payoffs |
| `data/current_cost_audit.csv` | Current spread/depth/fee evidence, not historical costs |

`partial` verdicts in the frontend schema can mean blocked or insufficient data;
the explicit status and caveats explain which. They are not partial statistical
support. A significant source diagnostic or gross price response is not a
validated trading opportunity.
