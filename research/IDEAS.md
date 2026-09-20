# The search for an "asbestos-grade" actionable finding (in progress)

Bar, from the Ukraine asbestos-roof project: (1) each row names a specific place; (2) someone is
responsible for it; (3) a known, affordable fix exists; (4) that party could not easily have made
the list themselves; (5) a viewer can look at the evidence and believe it. None of the validated-
sensor findings below clears it — they measure, they don't tell anyone what to go fix.

| Candidate | Folder | Row = | Who acts / fix | Status |
|---|---|---|---|---|
| Methane plumes on landfills with "renewable" landfill-gas plants | `fixlist_methane/` | landfill | operator, state air agency, credit certifiers / cover, wells, flare uptime | running |
| Who lives under the flares | `fixlist_flares/` | flare site + named schools/clinics | national oil cos, Zero Routine Flaring signatories / capture the gas | running |
| Clinics and schools in the dark (sub-Saharan Africa) | `fixlist_darkclinics/` | named facility | health ministries, donors / solar kits | running |
| Zone zero from the air (wildfire) | `fixlist_zonezero/` | house | owner, Fire Safe Council, fire dept / clear 0–5 ft | running |
| Still under a tarp (hurricanes) | `fixlist_tarps/` | house | recovery programs, NGOs / roof repair grants | running |
| Scout + critic for further ideas | `scout_actionable/` | — | — | running |

Seeds handed to the scout: poor-condition high-hazard dams currently overfull; tailings dams with
villages in the runout path; orphan wells near schools; cool-roof and schoolyard-shade targets;
green pools; acid mine drainage; brick kilns; civic-data joins (bridges × school buses, lead lines
× daycares, water violations × schools); Indonesian captive coal plants.

---

# Showcase connections — working list

Product framing: point the system at datasets, assign a mission to find a connection,
get back a tested verdict. These are candidate showcase examples. "Known" findings are
fine (they validate the machine); cite the prior art rather than claim novelty.

Status key: **VERIFIED** = an agent pulled real data and measured it · **PARTIAL** =
mixed/limited result · **PENDING** = agent still running · **DEAD** = tested, failed.

## Tier 1 — signal measured, demo-ready in a day

### 1. Dams from space → hydropower / blackout nowcast — VERIFIED (univariate)
- **Datasets:** PUDL EIA-923 monthly generation (1,701 US hydro plants, 2001–2026) ×
  satellite reservoir area (Global Water Watch API, keyless; Sentinel-2 SCL for gaps) ×
  Brazil ONS open data (175 reservoirs, daily) as second-country truth × GDELT blackout news.
- **Measured:** area vs generation, monthly deseasonalised / annual — Hoover 0.65/0.87,
  Shasta 0.55/0.88, Oroville 0.57/0.81, Glen Canyon 0.56/0.62, Fort Peck 0.54/0.66.
  Brazil area vs gauge level: Furnas 0.97, Sobradinho 0.90. GERD reservoir 11 km² (2020-03)
  → 862 km² (2026-02).
- **Weakness:** satellites see storage, not release (Furnas area vs flow×head only 0.11/0.29);
  needs an inflow proxy (GloFAS via Open-Meteo Flood API, keyless, must snap to river cell).
  Run-of-river has no signal. Monthly cadence.
- **Known or novel:** storage reconstruction is known (Mekong Dam Monitor, GWW); generation-label
  training + economic/blackout nowcast not found in prior art.
- **Why quants care:** Yunnan hydro ≈ 10% of China aluminium smelting; Zambia/DRC copper;
  Brazil power prices; LNG demand.
- **Next:** multivariate fit with inflow, out-of-sample; one blackout case end-to-end
  (Kariba 2024 / Ecuador 2024) vs GDELT lead time. *(scout, round 2, running)*

### 2. Gulf gas flaring as a production gauge — VERIFIED
- **Datasets:** VIIRS thermal hotspots via NASA GIBS vector tiles (keyless, 2012→yesterday;
  2.58M Gulf detections pulled in ~4 min, matches FIRMS exactly) × repo's Iran timeline ×
  Brent/TTF × GDELT.
- **Measured (Hormuz closure 4 Mar–8 Apr vs Oct–Feb baseline / vs same weeks 2025):**
  Iraq-Basra −78% / −73%; Qatar −59% / −56%; Saudi-East −60% / −16% (ambiguous);
  Iran-Khuzestan −5% / +31%; controls −9…−33%. Basra ~3,300 MW/night → <500 within two weeks,
  ahead of the "6.7 mb/d offline" figure dated 10 Mar.
- **Weakness:** one regime shift → no tradable lead (Brent r=−0.76 in levels, perm p=0.20;
  TTF p=0.002 but 5-day-diff r≈−0.24). Flare power ≠ barrels; report % change. March cloud.
- **Known or novel:** known — Payne Institute published the flaring story for this war.
  Our add: reported-vs-observed scoreboard tied to news and prices.
- **Build:** 10–12 h, reuses WarSignal registry/stats/Terminal. Scripts in `wardamage/`.

### 2b. Flaring round 2 — validated against production labels: DOWNGRADED to "outage alarm", not a gauge
- **Corrections to round 1:** Saudi-East −60% and Kuwait −36% were seasonal/cloud artifacts; with
  clear-sky normalisation vs same weeks 2025: Basra −65% (index 0.36 [0.27–0.46] vs 1.02
  [0.80–1.23]), Qatar −53%; Saudi-East +45%, Kuwait +14%, UAE +95%. Basra and Qatar survive.
- **US labels** (ND regulator flared volumes; EIA vented+flared), train 2012–18 / test 2019+:
  annual r 0.91 (Bakken) / 0.87 (Permian); YoY 0.61 / 0.57; month-on-month 0.19 / 0.23. Tracks
  FLARED VOLUME at annual/seasonally-adjusted scale; vs CRUDE PRODUCTION it fails (Permian MoM
  r=−0.00). Satellite series swings 4–7× by season vs label 1.18× (cause unidentified).
- **16 countries, 752 country-quarters YoY:** pooled r=0.53 (mismatched-country placebo 0.01).
  Carried by heavy-flaring producers: Libya 0.93, Yemen 0.78, Iran 0.58, Iraq 0.41; Saudi, Kuwait,
  UAE, Qatar, Oman ≈ 0. Natural experiments: Libya 2020 prod −89% / flare −89%; Yemen 2015
  −90/−90; but Abqaiq 2019 prod −14% / flare **+122%**, OPEC+ 2020 Iraq −15% / **+45%**,
  Kazakhstan outages **+305%** — when gas handling breaks, flaring goes UP. Sign matches in 71%
  of 21 episodes.
- **Calibration:** only flare drops deeper than ~50% carry information (median production −36%,
  10–90th pct −88…+16, n=26). Frozen pre-2025 model applied to 2026: only 2 of 7 Gulf countries
  inside the 80% interval (Iraq predicted −35% vs actual −67%; Qatar −16% vs −84%; UAE flare
  +471% while production −32%).
- **Defensible claim:** in a heavy routine-flaring producer, a sustained >50% drop in
  clear-sky-normalised flare power flags a major outage within ~a week (Basra alarm fired day 7,
  on 84–91% of the closure; Qatar day 14; controls in alarm 0–5% of war days). It cannot size the
  loss beyond "large". Misses Kuwait/Saudi/UAE despite 25–70% production losses.
- SNPP outage 27 Jul–10 Aug 2022 (+5 shorter in 2024–26) — pipelines now drop flagged days;
  headline r's move ≤0.07.
- **Strike scoreboard:** 72 news-dated events, built blind: 15 hits (21%); non-flare sites 28%,
  permanent-flare sites 13%; tank farms 4/8, depots 4/10, refineries 3/12; LNG/gas, petrochemical,
  steel, tankers, airbases 0. Placebo 0.76% per 72 h window. First overpass vs first GDELT article:
  median −2.2 h, +0.8 h after product latency → no usable lead.
- **Sentinel-2/-1 on strikes:** Tehran refinery burn scar ~7 ha, ranked 1st of 21 blobs blind,
  388 m from VIIRS point; Fujairah 3 Mar recovered by radar at +26 h (ranked 1st of 48, none in 42
  null looks). Ras Laffan and South Pars remain misses (damage sub-pixel; heat reads as emergency
  flaring). Demo image: `wardamage/s2s1_out/panel_tehran.png`.

### 3. Strike detection at non-flaring sites — PARTIAL
- Same data as #2 with a "novel hotspot cell" mask (81% of night detections sit in 1,018
  permanent flare cells, so naive spikes fail).
- **Hits:** Fujairah 0 detections in 14 months → 218/346/275 MW on 3–5 Mar, again 14–22 Mar
  (confirmed by Bloomberg/CNBC; both missing from `iran_timeline.csv`); Tehran refinery 763 MW
  on 7 Mar vs p99 46. Abqaiq 2019 historical check: detector flags exactly one day in six
  weeks, the right one.
- **Misses:** Ras Laffan and South Pars (18 Mar) — inside permanent flare fields.
- **Honest framing:** orbit is ≥8 h slower than news; it's better on magnitude and duration,
  not timing.

### 1b. Dams — scout round 2 (inflow proxy, zero-shot, blackout lead) — MIXED
- Time-split test R² vs EIA-923 (train <2017), season / +area / +inflow / +both: Hoover
  0.24/0.60/0.22/0.52; Glen Canyon −0.09/0.56/−0.41/0.03; Shasta 0.08/0.35/0.34/0.45; Oroville
  0.25/0.45/0.21/0.35; Fort Peck −0.16/0.29/0.30/0.31. **Area always beats season-only.** GloFAS
  inflow helps headwater dams, hurts regulated rivers.
- Zero-shot leave-one-dam-out on anomalies: r 0.37–0.70, R² 0.09–0.47 (Sobradinho 0.47/0.70).
  Pooled level model fails across hemispheres — predict anomalies only.
- **Kariba is a trap:** deep/steep, area doesn't track level (2019 reads −11%, 2024 +0.8%).
  Itezhi-Tezhi shows 2024 (−28–30%). Zambia news lead-lag NULL (r ≤ 0.28, news leads; GDELT
  coverage thin). Ecuador untested.

### 1c. Dams — full build at scale (1,365 reservoirs, 105 countries): REAL BUT MODEST, NOT AN EARLY WARNING
- **The scout's five dams were top-decile cases.** Across 399 US storage dams the median per-dam r
  (area anomaly vs generation anomaly) is 0.12; Hoover 0.61 and Shasta 0.57 replicate.
- Skill on anomalies, unseen dams + unseen years (2019–25), 327 US dams: area only −0.01;
  basin climate only 0.14; area + climate 0.12 (CI 0.08–0.15; median per-dam r 0.37); carry-over
  storage subset (residence ≥100 d, ≥10 km², n=112, exploratory) 0.17 / r 0.44. Damped persistence
  with a 3-month-old label (EIA's lag) 0.16; with last month's label 0.52 — persistence wins
  wherever fresh labels exist. Basin precipitation carries more skill than reservoir area.
- **Brazil zero-shot** (frozen US model vs ONS per-plant generation): storage reservoirs n=41,
  skill 0.29, median per-dam r 0.56, annual r 0.71; run-of-river n=27 as negative control −0.02.
  Satellite area vs ONS gauge volume median r 0.88 (storage), 0.14 (run-of-river).
- **47 countries vs Ember hydro capacity-factor anomalies:** median r 0.50 monthly, 0.64 annual;
  41 of 47 above 0.3; fails in Canada, Japan, Nigeria, Tajikistan; Norway fails in winter (ice).
- **US regional aggregation vs all EIA hydro:** California r 0.90 unseen dams / 0.85 unseen dams
  and years (3-month-old label: 0.52); Southeast 0.80/0.66; Plains 0.71/0.73; Colorado 0.55/0.35;
  Pacific NW 0.52/0.15 (fails).
- **Pre-registered alert rule REJECTED as early warning:** 674 alerts, precision 63% vs 43% base
  rate, recall 16%, median lead −3 months (fires after the shortfall starts). Country level ≈ null.
  News lead null (median r 0.02 at lag 0; only 15 of 47 countries pulled — GDELT 429s).
- **Headline cases:** 7 of 22 episodes showed a ≥10% deficit at onset. Wins: Guri 2016 (alert 15
  months ahead), Mtera 2015, Três Marias 2014–15, Itezhi-Tezhi 2024; Venezuela 2019 grid fault
  correctly shows nothing. Misses: Yunnan 2021–23, Vietnam 2023, Turkey 2021, Tanzania 2022.
  **Kariba fix:** own Sentinel-2 extraction of a shallow shore sector recovers the 2019, 2022,
  2024 drawdowns (r 0.52 vs load-shedding news at lag 0; news leads by 2 months at peak 0.58).
- **GERD** from own Sentinel-2: 15 km² river (2019) → 204 → 372 → 719 → 1,095 → 1,430 →
  ~1,500 km² peak (late 2025). Side effect: latest-state table flags drained reservoirs (Klamath
  Iron Gate −88%, Copco 2 −90%, Elwha −70%, Edenville −92%, a Dnipro reservoir −95%).
- Grid cross-check: satellite-predicted hydro anomaly vs actual thermal output r −0.39 (US West),
  −0.49 (Brazil zero-shot). Placebo: neighbour reservoir r 0.19 vs own 0.37 → about half the
  signal is regional drought. Plant↔reservoir matching agrees with GloHydroRes 96.5%.
- Files: `dams/figures/` (11 PNGs), `dams_latest.geojson`, findings.json (7 supported, 4 partial,
  2 rejected). Caveat: `08_model.py` not re-run after a refactor; chain never run end to end.

### 6. Missing hydro is replaced ~1:1 by fossil generation — VERIFIED (labels only)
- PUDL EIA-930, Western Interconnection monthly anomalies n=89: fossil −0.85 MWh per MWh hydro
  (controls wind/solar/trend, R²=0.64; raw r=−0.52). Null inside CAISO alone (r=−0.08; imports).
  Known; chaining to #1 ("the grid from space") is the novel part. Satellite-NO2 leg untested.

### 7. NYC lockdown: taxi trips collapse, roadside NO2 follows — VERIFIED
- NYC TLC × OpenAQ. Trips −96%. Fort Lee (GW Bridge) weekly r=0.89, NO2 −41% vs −24% same weeks
  2019; Jersey City r=0.87, −38% vs −3%. Known. Demo 9/10.
- Congestion pricing 2025 vs 2024: NULL (Jersey City +5.0% CI −4.5…+12.5; no keyless station
  inside the zone).

### 8. Methane super-emitter plumes sit on "renewable" landfill-gas power plants — VERIFIED
- Carbon Mapper API × PUDL plants. 20,382 US plumes: 12.7% within 1 km of an EIA plant vs 1.3%
  when shifted ~9 km; 76% of those are landfill-gas plants; 125 of 339 LFG plants (37%) have ≥1
  plume, 46 have ≥10. Overflight targeting bias uncorrected. LFG-plant framing appears unpublished.
  Generation vs leak rate: null (Spearman 0.05).

### 9. Smaller verified connections (all known)
- One airport thermometer → state electricity demand (ISD × EIA-930): Texas from DFW held-out
  2024 R² 0.70 (0.80 with hour/weekend); +2.9%/°C above 25 °C. NY from LGA 0.54/0.76, +4.0%/°C.
- TROPOMI NO2 vs ground NO2, Delhi: daily r=0.45 (n=148), weekly 0.67; lockdown −64% from space
  vs −26% ground midday.
- Rain → taxis (TLC × ISD): heavy-rain hours trips +11.0% (se 1.6), speed −5.0% (se 0.7).
- News → papers lag (GDELT × OpenAlex): mpox best lag 3 months r=0.61 (0.39 at lag 0), 8,149
  papers. ChatGPT 1 month but trend-confounded.
- West Texas airport wind → ERCOT wind generation: hourly r=0.47, daily 0.60; LGA placebo r=0.00.
- Airport visibility → PM2.5 (Delhi): daily r=0.66 but hold-out R² poor (0.16, −1.75).

### 10. Do orbit-measured signals predict market prices? — REJECTED (rigorous null) + sensor validated
- 53 pre-registered tests, 10,000-draw max-stat permutation, signals lagged for product latency,
  BH across the family. **0 of 46 liquid-market tests survive** (smallest q = 0.16); 1 had raw
  p<0.05 vs ~2.3 expected by chance. Sign matched the pre-registered mechanism 46% of the time.
  Placebos: 151 tests → 6.6% at p<0.05.
- Yunnan reservoirs → aluminium (10 tests) null; SHFE r=−0.02 (n=89). At 3 of 5 curtailment
  announcements the knowable satellite anomaly was positive; SHFE had already rallied 24%.
- Brazil reservoirs → utility equities null, **even using ONS's own stored-energy data** — no
  satellite proxy can do better. Zambia → copper/kwacha, US West → Henry Hub/PCG/EIX, flares →
  Brent/tankers, Rhine → BASF, Norway → Norsk Hydro: all null. Detectable |r| ≈ 0.13–0.26.
- **Physical tier, 5 of 7 survive (all lag 0):** Brazil 9-reservoir satellite composite vs ONS
  stored energy r=+0.75 on 3-month changes (+0.87 out of sample); vs marginal operating cost
  r=−0.45 (official storage −0.49); vs thermal share r=−0.49. Norway filling vs Nord Pool price
  r=−0.31 same week, gone a week later. Satellite does not predict next-3-month cost (r=0.04).
- Cautions found: geographic placebos aren't independent (Toktogul "predicts" Brazil storage
  r=0.34 — shared climate driver); flare series shows a simultaneous Libya/Algeria collapse in
  mid-2022 that looks like a sensor outage.
- Figures: `markets/figures/fig2_brazil_storage_cmo_equity.png`, `fig4_family_overview.png`.

## Tier 2 — awaiting results

### 4. Power plants from space (NO2 / steam plumes vs EPA CEMS) — VERIFIED, weak-to-moderate
- **Steam plumes (Sentinel-2, 5 US cooling-tower plants, 146 clear plant-days):** on/off AUC 0.96
  (only 10 off-days); plume area vs capacity factor Spearman 0.56 pooled; per plant Amos 0.81,
  Scherer 0.58, Gavin 0.57, Bowen 0.13, Miller 0.11. Median plume area off 0.000 → <35% 0.007 →
  35–70% 0.018 → >70% 0.079 km². Winter-only; summer plumes vanish. `s2_montage_gavin.png` is a
  ready demo image.
- **TROPOMI NO2 (16 isolated US coal plants, Apr–Sep 2025, 1,055 valid plant-days):** daily r per
  plant 0.05–0.56 (median ~0.3); plant-month means r=0.56 (n=75); cross-plant r=0.72 vs NOx but
  0.24 vs MW. Useful only at ~30-day aggregation.
- **Gulf/Iran (no labels):** NO2 enhancements 12–64 µmol/m² vs 2–10 for US coal, ~95% clear days;
  big visible winter stack plumes at Shahid Rajaee and Neka; nothing visible at Shoaiba. No
  consistent change in the June 2025 war window.
- **Kill-shots:** no foreign labels and ~10x NOx/MWh spread → absolute MW abroad is unfalsifiable
  (output a per-plant z-score with US-calibrated error bars instead); daily SNR ≈ 1.
- **Best honest design:** train on US CEMS, test on Australia (AEMO 5-min per-unit data, keyless —
  believed, not tested). ~15 h full build, ~8 h for the Sentinel-2 on/off fallback.
- Known: Climate TRACE / WattTime / TransitionZero (since 2019); Beirle et al. NOx catalogue
  (1,139 sources). Works mainly for wet-cooled/wet-scrubbed plants (~4% of plants, ~43% of
  emissions); useful after monthly averaging.
- Still-open angles: regional aggregation validated against EIA-930 hourly generation by fuel;
  event-specific nowcast (Iran/Gulf); orphan NOx hot spots with no plant match (captive plants).
- Natural pair with #1: "the grid from space" — thermal NO2 should rise as reservoirs fall.

### 4b. Power plants round 2 — scaled, out-of-country, calibrated: relative signals hold, levels don't
- **Sentinel-2 plumes, 46 US plants, 3 years, 2,590 usable scenes (537 off-scenes), leave-whole-
  plants-out:** on/off AUC 0.86 (natural-draft towers 0.89; mechanical-draft ~0.72); Spearman vs
  capacity factor 0.57 (natural-draft 0.65; within on-state ~0.38); load-tercile accuracy 0.55 vs
  chance 0.33. Raw-area AUC 0.97 below 5 °C, 0.67 above 25 °C. Weather features add +0.07
  Spearman (CI 0.03–0.10); weather-only control has no skill (AUC 0.56). Cloud leakage reduced,
  not eliminated. Label-free source finder REJECTED (locked onto ash dams at 6 of 8 AU plants).
- **Zero-shot Australia (AEMO 5-min per-unit data, keyless, 37 months):** rank transfers — pooled
  Spearman 0.37 on 7 tower plants; Mt Piper 0.61, Loy Yang 0.61, Yallourn 0.51, Bayswater 0.45;
  low-vs-high load quartile AUC up to 0.96. Level does NOT transfer (CF bias −0.13). Tarong 0.17,
  Stanwell 0.27. Controls: air-cooled plants ≈ 0; once-through Eraring −0.37 (spurious → noise
  floor ~|0.3|).
- **TROPOMI NO2, 58 isolated US plants, 1,096 days:** daily REJECTED (median r 0.27; wind
  rotation doesn't help; 16 of 58 below detection). 30-day index on 42 detectable plants, held out
  by plant: r=0.48 vs CEMS NOx; 80% band coverage 0.795. Outage detection (147 real 30-day
  outages, 25 plants): AUC 0.81, 45% caught at 5% false alarms. Seasonality placebo: r 0.52 this
  year vs 0.21 same dates a year off. Tracks NOx, not MW (r ~0.3). Australia: median 30-day r vs
  MW 0.44 (−0.09…0.87). When NOx is unchanged the index spans 0.58–1.56.
- **SO2 separates oil from gas plants:** AUC 0.95 (14 oil, 27 gas; NO2 control 0.70). Shahid
  Rajaee is listed as gas but shows strong SO2.
- **Regional aggregation mostly fails:** median monthly r vs EIA-930 fossil 0.40 (0.21
  deseasonalised); works in rural coal regions (SWPP 0.65, WACM 0.64), not urban (PJM 0.06).
- **2026 war, 41 hand-checked sites (35 contaminated by cities/refineries; 5 clean):** index vs
  same weeks 2025 — Iranian plants ×0.60, Iraqi ×0.53, Gulf ×0.79; BUT Iranian city centres ×0.54,
  Gulf cities ×0.70; far-from-theatre cities ×1.26. A real theatre-wide NO2 drop, not attributable
  to power plants. Recovery within 60 days: Gulf 0.99, Iran 0.81.
- **Orphan NOx:** Sulawesi/Halmahera box 8 hot spots, 4 with zero listed capacity within 25 km;
  Sentinel-2 shows large industrial complexes at 4 of 5 checked (Morowali 98 µmol/m² vs 280 MW
  listed). Park names unverified. Middle East: 122 orphans, mostly unchecked.
- Demo: `powerplants/figs/montage_gavin_us.png`, `montage_loyyang_au.png`, `s2_summary.png`,
  `foreign_no2_index.png`. 13 claims in findings.json (4 supported, 7 partial, 2 rejected).

### 5. PM2.5 in cities with no monitors (OpenAQ × CAMS × ERA5 × VIIRS AOD) — original pitch DEAD, negative result usable
- **Model barely beats CAMS and not where it matters:** station-annual RMSE 11.2 → 10.4 µg/m³
  leave-countries-out (n=1,291; MAE gain 0.99, 95% CI [0.09, 2.23]); no better than CAMS under
  leave-region-out (r 0.59 vs 0.67). At stations >35 µg/m³ it shrinks predictions (obs 49.6,
  CAMS 37.9, GBM 30.1). Ranked city list correlates 0.92 with raw CAMS; N'Djamena predicted 19
  vs ~92 reported.
- **Usable finding — CAMS bias atlas:** Europe −4%, South Asia −8%, Sub-Saharan Africa −26%,
  MENA −31%, Central Asia −35%, South America −58%; Tajikistan −72%, Chile −63%, USA +28%.
  Daily r 0.5–0.7 almost everywhere: timing right, level wrong.
- **Leakage ladder:** random CV R² 0.57 → leave-country 0.43 → leave-region 0.31.
- **Value of a monitor:** ~3 in-country stations (MAE 4.80) beat any amount of foreign training
  data (5.06).
- **Coverage:** 718 of 1,210 cities ≥500k have no reference-likely PM2.5 monitor in OpenAQ within
  25 km — but 294 are China (measures, left OpenAQ). "Unmonitored" = "not in OpenAQ".
- Prior art covers both map and placement score (Atmos. Env. 2022; arXiv 2604.22787). 10–12 h for
  the audit version. Wrong vehicle for a "revealed from orbit" story.

## Tier 3 — fallbacks / add-ons
- **Methane plumes × operators** (Carbon Mapper API keyless, 36,391 plumes × PUDL plants):
  6–8 h, a spatial join rather than a model; tasking-biased sampling. Well covered already.
- **Construction progress vs EIA-860M status** (8,006 generators ever under construction,
  4,857 solar; Sentinel-2 chips): 12–16 h; US "hidden" window is only ~2 months; chip pulls slow.
- **Coal stockpiles** (receipts − burn as label): 16 h+, area≠volume, needs hand polygons.

## Dead
- **Yunnan reservoir area → aluminium price:** r=0.06 vs next-3-month return (n=144).
- **Satellite reservoir deficit leads blackout news (Zambia):** null; Kariba area blind to level.
- **Reactor on/off from Landsat thermal:** Pilgrim on vs off water-temp spread not separable
  (1.2–5.8 °C on, 0.5–5.9 °C off); ~13 clear scenes/yr; 23 s per chip.
- **"Space sees it before the news":** false in every case checked.
- **WarSignal Round 2 trade rules:** 0 of 209 hypotheses survive BH FDR at q=0.05
  (5 at q=0.10; permutation floor p=0.002 from ~500 shuffles limits resolution).

## Data-access cheat sheet (all tested anonymously unless noted)
| Source | Keyless | Note |
|---|---|---|
| PUDL `s3://pudl.catalyst.coop/nightly/` | yes | EIA-923, 860M, plants; CEMS parquet 4.9 GB |
| NASA GIBS VIIRS thermal vector tiles | yes | full FIRMS attributes, ~1 day latency |
| FIRMS country-year CSVs | yes | 2019–2024 only; 2025/26 → 404; API needs MAP_KEY |
| Global Water Watch API | yes | 1.5–6 s/reservoir; GERD missing; licence unchecked |
| Brazil ONS `s3://ons-aws-prod-opendata/` | yes | daily level/inflow/turbined/spill 2000–2026 |
| Open-Meteo Flood (GloFAS) | yes | snap to river cell or you get zeros |
| Sentinel-2 via Earth Search STAC | yes | 1.6–3.6 s/tile on overviews |
| Planetary Computer (S1, S5P, Landsat) | yes | anonymous SAS token; Landsat chip ~23 s |
| Sentinel-5P `s3://meeo-s5p/COGT/OFFL/` | listing only | ~34 MB/orbit |
| Carbon Mapper API | yes | terms not read |
| Black Marble VNP46 | **no** | Earthdata login |
| VIIRS Nightfire / EOG | **no** | OpenID login |
| OpenAQ API | **no** | key; S3 archive is anonymous |
| NRC reactor status | flaky | 403 to curl, last 365 days only |
