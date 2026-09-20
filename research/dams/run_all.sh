#!/bin/sh
# Reproduce everything in order. All network pulls are cached under cache/ and data/; re-runs are offline where possible.
set -e
PY=.venv/bin/python
$PY 00_fetch_pudl.py            # PUDL tables (anonymous S3)
$PY 01_gww_catalogue.py || true # GWW reservoir catalogue (skips if already built)
$PY 02_ons_pull.py              # Brazil ONS generation / hydrology (slow: ~730 MB streamed)
$PY 03_match_plants.py          # plants <-> reservoirs (needs data/hydrolakes_pts.parquet, data/glohydrores.csv)
$PY 04_pull_areas.py            # GWW raw area series -> cleaned monthly
$PY 06_build_panel.py           # panel + pre-registered storage filter
# 07 needs (deleted after use to save disk; outputs kept in data/basin_climate.parquet, data/basins.parquet):
#   data/hybas/hybas_{na,sa,af,as,eu,au,si,ar}_lev07_v1c.zip  <- https://data.hydrosheds.org/file/hydrobasins/standard/
#   data/clim/precip.mon.mean.1x1.nc <- https://downloads.psl.noaa.gov/Datasets/precl/1.0deg/ ; data/clim/air.mon.mean.nc <- .../Datasets/ghcncams/
$PY 07_basin_climate.py         # HydroBASINS upstream trace x PREC/L + GHCN-CAMS
$PY 06_build_panel.py
$PY 08_model.py                 # validation + final models
$PY 10_transfer_brazil.py
$PY 11_transfer_national.py
$PY 12_gdelt.py                 # hours under the 1 req / 5 s limit; safe to interrupt
$PY 13_alerts.py
$PY 14_leadlag.py
$PY 15_case_studies.py
$PY 05_gerd_s2.py               # ~3 h of anonymous COG reads
$PY 05b_s2_extra.py
$PY 17_latest_geojson.py
$PY 18_grid_crosscheck.py
$PY 19_transfer_norway_storage.py
$PY 20_robustness.py
$PY 22_regional_aggregate.py
$PY 23_news_leadlag.py
$PY 16_figures.py
$PY 21_findings.py
