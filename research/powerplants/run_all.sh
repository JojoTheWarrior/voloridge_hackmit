#!/bin/zsh
# Reproduction order for round 2 (all anonymous access). Long steps are marked; everything is resumable/skips existing outputs.
P=.venv/bin/python
# --- labels / plant lists
$P select_plants.py                                   # US candidates from CEMS 2024 + EIA-860 cooling  (~5 min)  -> us_plant_candidates.csv ; plants_s2_us.csv built inline in round-2 notes
$P cems_fetch2.py plants_s2_us.csv cems_s2_us.parquet 2023       # (~15 min)
$P cems_fetch2.py plants_no2_us.csv cems_no2_us.parquet 2023     # (~10 min)
$P aemo_fetch.py                                      # AEMO 5-min SCADA, 37 months (~1.1 GB download)
# --- Sentinel-2 plume study
$P s2_extract2.py plants_au.csv 2023-07-01 2026-06-30 s2/au ; $P s2_extract2.py plants_s2_us.csv 2023-07-01 2026-06-30 s2/us ; $P s2_extract2.py plants_iran_iraq.csv 2024-10-01 2026-09-15 s2/ir   # (~2 h)
$P osm_towers.py plants_s2_all.csv osm_towers.csv ; $P osm_towers.py plants_iran_iraq.csv osm_towers_ir.csv
$P weather_fetch.py plants_s2_all.csv 2023-07-01 2026-06-30 weather_s2.parquet
$P s2_features.py s2/au plants_s2_all.csv osm_towers.csv s2_features_au.csv ; $P s2_features.py s2/us plants_s2_all.csv osm_towers.csv s2_features_us.csv ; $P s2_features.py s2/ir plants_iran_iraq.csv osm_towers_ir.csv s2_features_ir.csv
$P s2_model.py ; $P s2_model2.py ; $P s2_summary_fig.py ; $P s2_iran.py
$P s2_montage.py s2/us 8102 us figs/montage_gavin_us.png "Gavin" ; $P s2_montage.py s2/au AU_LOYYANG au figs/montage_loyyang_au.png "Loy Yang" ; $P s2_montage.py s2/au AU_MTPIPER au figs/montage_mtpiper_au.png "Mt Piper"
# --- TROPOMI
$P s5p_region.py conus no2 2023-07-01 2026-06-30 ; $P s5p_region.py me no2 2025-01-01 2026-09-10 ; $P s5p_region.py me so2 2025-01-01 2026-09-10 ; $P s5p_region.py au no2 2024-07-01 2026-06-30 ; $P s5p_region.py idn no2 2025-07-01 2026-06-30   # (~3 h, ~50 GB streamed)
$P weather_fetch.py plants_no2_us.csv 2023-07-01 2026-06-30 wind_no2_us.parquet "wind_speed_100m,wind_direction_100m,temperature_2m" 5
$P weather_fetch.py plants_foreign2.csv 2025-01-01 2026-09-10 wind_foreign2.parquet "wind_speed_100m,wind_direction_100m,temperature_2m,relative_humidity_2m" 6
$P weather_fetch.py control_sites.csv 2025-01-01 2026-09-10 wind_controls.parquet "wind_speed_100m,wind_direction_100m,temperature_2m,relative_humidity_2m" 6
$P no2_index.py conus no2 plants_no2_us.csv wind_no2_us.parquet no2_daily_us.csv ; $P no2_calibrate.py ; $P no2_placebo.py ; $P no2_fig.py ; $P no2_regional.py
$P no2_index.py me no2 plants_foreign2.csv wind_foreign2.parquet no2_daily_foreign.csv ; $P no2_index.py me so2 plants_foreign2.csv wind_foreign2.parquet so2_daily_foreign.csv ; $P no2_foreign.py ; $P so2_analysis.py
$P no2_index.py me no2 control_sites.csv wind_controls.parquet no2_daily_controls.csv ; $P no2_controls.py
$P no2_index.py au no2 plants_au.csv wind_au.parquet no2_daily_au.csv ; $P no2_au.py      # wind_au.parquet = AU rows of weather_s2.parquet
$P no2_orphans.py idn orphans_idn ; $P no2_orphans.py me orphans_me
$P build_findings.py ; $P build_findings2.py ; $P build_findings3.py
