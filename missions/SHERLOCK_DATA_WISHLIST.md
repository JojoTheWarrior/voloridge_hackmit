# Sherlock data wishlist — download shopping list

Everything below is free. Window for all series: **2025-01-01 → today** (the finance store
already starts 2025-01-02; the mission window in `warsignal/config.py` is 2025-03-01). Each item
says what it unlocks, the exact endpoint, auth, format, rough size, and the indicator it becomes.

Plumbing convention (same as every existing source): a fetcher `warsignal/fetch/<src>.py`
writing raw files to `data/raw/<src>/` (+ `_manifest.jsonl` via `warsignal.fetch.common.manifest`),
an indicator module `warsignal/indicators/<src>.py` that `register()`s float daily
`pandas.Series` with a tz-naive `DatetimeIndex`, imported from `warsignal/indicators/__init__.py`.
Hypotheses then use the normal `[signal -> target]` tag. Add any new tickers to the finance
fetch list (`warsignal/fetch/finance.py`) so `finance.<TICKER>.log_return` exists.

Priority order reflects (a) how cleanly it upgrades a Sherlock idea we already have a mission
for and (b) effort: items 1–4 are ~10 minutes each; 5–7 ~20 minutes each; 8–9 need an account.

---

## 1. USGS river stage / discharge — Mississippi system (idea #2, upgrades S-0011)

* **Why:** barge draft limits (low water) and lock closures (high water) move grain basis,
  barge freight and fertilizer delivered cost; the stage at St. Louis / Memphis is the
  observable, `ZC=F`, `ZW=F`, `ZS=F`, `CF`, `MOS`, `NTR`, `ADM`, `BG` are the targets.
* **Source:** USGS Water Services daily values (NWIS). Legacy endpoint (still live, JSON):
  ```
  https://waterservices.usgs.gov/nwis/dv/?format=json&sites=07010000,07032000,07374000,05587450,07020500&parameterCd=00065,00060&startDT=2025-01-01&endDT=2026-09-20
  ```
  Sites: `07010000` Mississippi at St. Louis MO, `07032000` Memphis TN, `07374000` Baton Rouge LA,
  `05587450` Grafton IL (above the Missouri confluence), `07020500` Chester IL. Parameters:
  `00065` gage height (ft), `00060` discharge (cfs). USGS is migrating NWIS to
  `https://api.waterdata.usgs.gov/ogcapi/v0/collections/daily/items?monitoring_location_id=USGS-07010000&parameter_code=00065&datetime=2025-01-01/..` (OGC API, JSON/CSV) —
  if the legacy call 404s, use that; an API key is optional (rate limit only).
* **Auth:** none. **Format:** JSON (`value.timeSeries[].values[].value[]` with `dateTime`,
  `value`). **Size:** < 1 MB total.
* **Indicator:** `hydrology.mississippi.<site>.stage_ft`, `.discharge_cfs`, plus
  `hydrology.mississippi.st_louis.stage_anomaly` (day-of-year mean removed). Test
  `[hydrology.mississippi.st_louis.stage_ft -> finance.ZC=F.log_return]` (−, low water = wider
  basis but futures?) and vs `finance.CF.log_return` (+ for fertilizer priced delivered).

## 2. USDA Grain Transportation Report — barge rates & lock tonnage (idea #2)

* **Why:** the *market's* own reading of river conditions; weekly barge freight (St. Louis
  $/ton, % of tariff) and grain barge movements through Mississippi Lock 27.
* **Source:** USDA AMS GTR datasets page
  `https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets` — files
  "Barge Rates" (`Table 10`) and "Grain Barge Movements" (`Table 9` / weekly Lock 27 tonnage),
  Excel/CSV, updated Thursdays. Historical lock tonnage by lock/month from USACE LPMS
  "Corps Locks" (`https://corpslocks.usace.army.mil/lpwb/f?p=121`, tonnage report → CSV) if
  monthly is enough.
* **Auth:** none. **Format:** xlsx. **Size:** < 5 MB.
* **Indicator:** `logistics.barge.st_louis_rate_pct_tariff` (weekly, `freq="W"`),
  `logistics.barge.lock27_grain_tons`. Weekly aligns with the existing weekly resample in
  `warsignal/analysis/stats.py` (`W-MON`).

## 3. NRCS SNOTEL snow-water-equivalent (idea #5, upgrades S-0007/S-0008)

* **Why:** snowpack in Feb–Apr *anticipates* Columbia/Colorado hydro output in May–Jul, which
  displaces gas burn (mechanism confirmed in `SHERLOCK.md`). Targets: `NG=F`, `DHHNGSP`,
  `XLU`, Pacific-NW utilities (`IDA`, `PNW`, `AVA` — add to finance list).
* **Source:** NRCS AWDB REST API (no key):
  ```
  https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1/data?stationTriplets=1069:CO:SNTL,1070:CO:SNTL,835:WA:SNTL,970:WA:SNTL,1116:OR:SNTL,1099:ID:SNTL&elements=WTEQ&duration=DAILY&beginDate=2025-01-01&endDate=2026-09-20&periodRef=END
  ```
  Get station triplets for the Columbia (WA/OR/ID/MT) and Upper Colorado basins from
  `.../services/v1/stations?networkCds=SNTL&stateCds=WA,OR,ID,MT,CO,UT,WY`. Basin-average
  "% of median" is also published as CSV by the Report Generator
  (`https://wcc.sc.egov.usda.gov/reportGenerator/`).
* **Auth:** none. **Format:** JSON (`[{stationTriplet, data:[{stationElement, values:[{date,value}]}]}]`). **Size:** < 5 MB for ~50 stations.
* **Indicator:** `snow.columbia.swe_in` (mean over basin stations), `snow.columbia.swe_pct_median`,
  `snow.colorado.swe_in`. Hypothesis to run first:
  `[snow.columbia.swe_pct_median -> finance.NG=F.log_return]` (−) at the weekly resample.

## 4. Daily hydro generation by balancing authority — EIA-930 (idea #5)

* **Why:** turns the monthly PUDL hydro series into a *daily* one for BPA/CAISO, so the trade
  rule can actually fire.
* **Source:** EIA API v2 (free key from `https://www.eia.gov/opendata/register.php`):
  ```
  https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/?api_key=KEY&frequency=daily&data[0]=value&facets[respondent][]=BPAT&facets[respondent][]=CISO&facets[respondent][]=US48&facets[fueltype][]=WAT&facets[fueltype][]=NG&facets[fueltype][]=SUN&start=2025-01-01&sort[0][column]=period&sort[0][direction]=asc&length=5000
  ```
  (`WAT` hydro, `NG` gas, `SUN` solar; paginate with `offset`). PUDL also republishes EIA-930
  generation by fuel (`core_eia930__hourly_generation_fuel_type` on the same S3 bucket used by
  `warsignal/fetch/pudl.py`) — check the size header first; it may exceed the 400 MB guard.
* **Auth:** EIA API key (free, instant). **Format:** JSON rows `{period, respondent, fueltype, value}`. **Size:** ~2 MB.
* **Indicator:** `utility.BPAT.hydro_mwh_daily`, `utility.US48.gas_mwh_daily`,
  `utility.US48.solar_mwh_daily`, `utility.CISO.solar_mwh_daily`. Also gives the *direct*
  mechanism test for idea #4: `[weather.houston.radiation -> utility.ERCO.solar_mwh_daily]`
  (add `ERCO` to the respondent facet).

## 5. NASA/NOAA VIIRS Nightfire (VNF) — flare & furnace detections (ideas #1, #6, #8; upgrades S-0002..S-0006, S-0013)

* **Why:** the real "night heat" observable: sub-pixel combustion sources with fitted
  temperature (flares ~1800 K, furnaces/steel ~1200–1600 K) and radiant heat, nightly,
  global. Count/RH sum inside polygons around Donaldsonville/Geismar (ammonia), Sabine Pass /
  Cameron / Corpus Christi (LNG), Ras Laffan, Basrah/Rumaila, Asaluyeh (Iran South Pars),
  and steel belts (Tangshan, Pohang).
* **Source:** Earth Observation Group, Colorado School of Mines:
  `https://eogdata.mines.edu/products/vnf/` → nightly CSV per satellite
  (`VNF_npp_dYYYYMMDD_noaa_v30-ez.csv.gz` and `VNF_j01_...` for NOAA-20), fields
  `Date_LTZ, Lat_GMTCO, Lon_GMTCO, Temp_BB, RHI, RH, Area_BB, Cloud_Mask`. Download via
  `https://eogdata.mines.edu/nighttime_light/...` style authenticated URL after login, or the
  EOG API token (`https://eogdata.mines.edu/eog/EOG_sensitive_contents`).
* **Auth:** free EOG account (email registration, instant). **Format:** gzipped CSV, one file
  per night per satellite. **Size:** ~2–10 MB/night global → ~3–6 GB for the window; filter to
  bounding boxes on download and keep < 100 MB.
* **Indicator:** `flare.<site>.n_detections`, `flare.<site>.rh_mw` (sum of radiant heat),
  `flare.<site>.temp_mean_k` for sites in a small `flare_sites.json`
  (`{"donaldsonville": [30.06,-90.99, 15km], "sabine_pass": [29.75,-93.87, 15km],
  "ras_laffan": [25.90,51.55, 20km], "rumaila": [30.35,47.35, 60km], "asaluyeh": [27.47,52.61, 30km]}`).
  First hypotheses: `[flare.donaldsonville.rh_mw -> finance.CF.log_return]` (+),
  `[flare.sabine_pass.n_detections -> finance.LNG.log_return]` (upsets: −),
  `[flare.ras_laffan.rh_mw -> finance.TTF=F.log_return]` (+).

## 6. Sentinel-5P TROPOMI NO2 / SO2 at plant coordinates (ideas #1, #6, #8)

* **Why:** replaces the city-box CAMS proxy with a 5.5 km observation over the actual plant.
* **Source (easiest):** Google Earth Engine, image collections `COPERNICUS/S5P/OFFL/L3_NO2`
  (band `tropospheric_NO2_column_number_density`) and `COPERNICUS/S5P/OFFL/L3_SO2`
  (`SO2_column_number_density`); daily `reduceRegion(mean)` over a 10 km buffer per site,
  export one CSV per site (`ee.batch.Export.table.toDrive`). Needs a free GEE account /
  Cloud project (`earthengine authenticate`).
  **Source (no Google):** Copernicus Data Space Sentinel Hub Statistical API
  `https://sh.dataspace.copernicus.eu/api/v1/statistics` with collection `sentinel-5p-l2`,
  evalscript returning `NO2`; OAuth client credentials from `https://shapps.dataspace.copernicus.eu/dashboard/`.
* **Auth:** free account either way. **Format:** CSV `date,mean,count`. **Size:** < 1 MB.
* **Indicator:** `tropomi.<site>.no2`, `tropomi.<site>.so2` (same `flare_sites.json`; add
  `tangshan` [39.63,118.18], `pohang` [36.02,129.37], `jamnagar` [22.35,69.85] for #6).
  Hypotheses mirror §5 with `tropomi.*` in place of `flare.*`; for #6 target `HG=F`, `FCX`,
  `ALI=F`, `X`, `CLF`, `NUE` (add the last three to the finance list).

## 7. Global Fishing Watch — Peru anchovy fleet effort (idea #7)

* **Why:** Peruvian anchoveta is ~1/3 of world fishmeal; fleet effort/closures in the
  Chimbote–Callao box lead fishmeal prices and salmon-farmer feed costs. Targets (add to finance
  list): `MOWI.OL`, `SALM.OL`, `LSG.OL`, `BAKKA.OL`, `AUSS.OL` (owns Austral, a fishmeal
  producer), `GSF.OL`.
* **Source:** GFW API v3 (`https://globalfishingwatch.org/our-apis/documentation`):
  ```
  POST https://gateway.api.globalfishingwatch.org/v3/4wings/report?spatial-resolution=LOW&temporal-resolution=DAILY&group-by=FLAG&datasets[0]=public-global-fishing-effort:latest&date-range=2025-01-01,2026-09-20&format=JSON
  body: {"geojson": {"type":"Polygon","coordinates":[[[-82,-4],[-70,-4],[-70,-18.5],[-82,-18.5],[-82,-4]]]}}
  ```
  Returns daily apparent fishing hours by flag (filter `PER`). Alternatively use
  `region: {"dataset":"public-eez-areas","id":<Peru EEZ id from /v3/datasets/public-eez-areas/context-layers>}`.
* **Auth:** free API token (register at `https://globalfishingwatch.org/our-apis/tokens`, instant).
  **Format:** JSON `entries[].{date, hours, flag}`. **Size:** < 1 MB.
* **Companion (landings):** IMARPE daily anchoveta landings bulletins
  (`https://www.imarpe.gob.pe/imarpe/` → "Reporte diario de desembarque", PDF; scrape the
  season total) and PRODUCE monthly landings; NOAA FOSS for US landings is *not* relevant here.
* **Indicator:** `fishing.peru.anchovy_hours`, `fishing.peru.anchovy_hours_7d`. Hypothesis:
  `[fishing.peru.anchovy_hours_7d -> finance.MOWI.OL.log_return]` (+: more fishing = cheaper feed)
  with a 5–10 day lag; also vs `finance.AUSS.OL.log_return`.

## 8. Wastewater chemistry — Las Vegas & cruise ports (idea #9)

* **Why:** norovirus/influenza/SARS-CoV-2 load in Clark County (Las Vegas) or Miami-Dade
  sewage leads visitor-illness headlines and cancellations; targets `LVS`, `WYNN`, `MGM`,
  `CZR`, `CCL`, `RCL`, `NCLH` (all already in the finance list or trivial to add).
* **Source A:** WastewaterSCAN (Stanford/Emory) `https://data.wastewaterscan.org/` →
  "Download data" CSV (site, date, target incl. `Norovirus GII`, `Influenza A`, `SARS-CoV-2`,
  `RSV`, normalised to PMMoV). Filter `state == NV` (Las Vegas / Henderson plants) and `FL`
  (Miami-Dade). No auth, CSV, ~50 MB full file.
* **Source B:** CDC NWSS public metric data on data.cdc.gov, dataset id `2ew6-ywp6`
  (`https://data.cdc.gov/resource/2ew6-ywp6.json?county_names=Clark&wwtp_jurisdiction=Nevada&$limit=50000`),
  SARS-CoV-2 only, 15-day percent change and percentile. No auth (app token optional), JSON.
* **Indicator:** `wastewater.las_vegas.norovirus`, `wastewater.las_vegas.influenza_a`,
  `wastewater.miami.norovirus`. Hypothesis:
  `[wastewater.las_vegas.norovirus -> finance.LVS.log_return]` (−, 3–10 d) and
  `[wastewater.miami.norovirus -> finance.CCL.log_return]` (−). Sampling is 2–3×/week →
  forward-fill *the signal only* to daily, never the returns.

## 9. Sentinel-2 lithium evaporation ponds (idea #3)

* **Why:** pond area / brine colour at Salar de Atacama tracks SQM and Albemarle brine
  inventory ahead of quarterly production numbers. Targets: `SQM`, `ALB`, `LAC`, `PLS.AX`
  (add to finance list).
* **Source:** Google Earth Engine `COPERNICUS/S2_SR_HARMONIZED` (5-day revisit, 10 m), filter
  `CLOUDY_PIXEL_PERCENTAGE < 20`, polygons for the SQM (~-23.6, -68.3) and Albemarle
  (~-23.75, -68.25) pond complexes; per image compute water area via NDWI > 0.1 and mean
  B2/B3/B4 reflectance of the ponds (colour ≈ concentration stage). Export CSV per operator.
  Alternative without GEE: Copernicus Data Space openEO (`https://openeo.dataspace.copernicus.eu`)
  with the same reducer.
* **Auth:** free GEE / CDSE account. **Format:** CSV `date,water_area_km2,mean_b4,mean_b3,mean_b2`.
  **Size:** < 1 MB (never download the tiles).
* **Indicator:** `satellite.atacama_sqm.pond_area_km2`, `satellite.atacama_sqm.pond_redness`
  (B4/B3). Irregular 5–10 day cadence → use the weekly resample. Hypothesis:
  `[satellite.atacama_sqm.pond_area_km2 -> finance.SQM.log_return]` (+, weeks).

## 10. (Low priority) Aircraft / vehicle traffic at plants (idea #8 "traffic")

* OpenSky Network REST `https://opensky-network.org/api/states/all?lamin=..&lomin=..&lamax=..&lomax=..`
  is live-only (no history without a research Trino account) — only useful if we start
  logging now. ADS-B Exchange historical is paid. Road traffic (TomTom/HERE) is paid. Skip
  unless a teammate already has an OpenSky research login; VIIRS Nightfire (§5) is the better
  "activity" proxy for LNG plants.

---

### Suggested first hour for the teammate

1. §1 USGS + §3 SNOTEL + §4 EIA-930 (three keyless/instant-key JSON pulls, one fetcher each).
2. §5 VNF: register, download the last 90 nights for the Gulf Coast box only, build
   `flare.donaldsonville.rh_mw` and re-run S-0002 with it.
3. §7 GFW token + one POST → `fishing.peru.anchovy_hours`, add the Oslo salmon tickers to
   `warsignal/fetch/finance.py`, re-fetch finance.
