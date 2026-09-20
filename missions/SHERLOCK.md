# Sherlock missions — strange observables that (might) predict a security

Round tag `sherlock`, mission ids `S-0001..S-0014`, status files in `missions/status/S-*.json`,
run folders in `missions/runs/20260920-205..218-*`. All runs use `--brain heuristic` (no API keys
on the research box), the standard Round 2 trade rule (20d rolling z > 1 → hold target for the
best positive lag, pre-war fit `< 2026-02-28` / war test `>= 2026-02-28`, see
`ROUND2_RUBRIC.md`) and the repo window `2025-03-01..today`.

Nine brainstorm ideas were triaged against the data already in the repo. Six could be attacked
with *proxies* (Copernicus CAMS combustion gases stand in for thermal/flare imagery, Open-Meteo
radiation stands in for cloud cover, EIA-923 hydro generation stands in for snowpack/reservoirs,
Oklahoma City weather stands in for the Corn Belt / river system). Three (#3 lithium ponds,
#7 fishing fleets, #9 wastewater) need data we do not have — see `SHERLOCK_DATA_WISHLIST.md`.

## Results table

Columns: r = contemporaneous Pearson (Spearman in brackets); lag = best lead lag (positive = signal
leads target) with r at that lag; perm p = circular-shift permutation p at the best lag (Bonferroni
over 21 lags in brackets); trade = all-sample rule stats (n trades / hit rate / mean excess return
per trade vs unconditional baseline / sharpe-like); pre → war = excess return per trade in the
pre-war fit and the out-of-sample war test; Jev = heuristic judge validity/interest/unexpected/
**actionability** (0–10).

| Idea | Testable now? | Proxy (signal → target) | Mission | r (sp) | lag, r | perm p (bonf) | n | trade n / hit / excess / sharpe | pre → war excess | Jev V/I/U/**A** | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1+8 Night heat/light at fertilizer & LNG plants → gas | proxy | Houston CAMS NO2 → NG=F log ret (+) | S-0001 | −0.19 (0.00) | 0d, −0.19 | 0.02 (0.42) | 390 | 55 / 45% / −0.94% / −0.92 | −0.90% → −1.03% | 0/2/2/**0.1** | null — Pearson driven by outliers (Spearman 0), wrong sign, rule loses money |
| 1 Fertilizer plant heat → CF | proxy | Houston CAMS SO2 → CF log ret (+) | S-0002 | −0.06 (−0.04) | +3d, +0.08 | 0.82 (1.0) | 389 | 35 / 60% / **+0.38%** / **+1.94** | **+0.44% → +0.28%** | 0/2/2/**8.6** | **interesting** — no linear correlation, but the tail rule (SO2 z>1 → long CF 3d) is profitable and stable across the war split |
| 8 LNG flaring → Cheniere | proxy | Houston CAMS CO → LNG log ret (+) | S-0003 | −0.02 (−0.08) | −4d | 0.58 (1.0) | 389 | 48 / 54% / +0.03% / +0.44 | +0.10% → −0.09% | 0/2/2/4.2 | null |
| 8 Ras Laffan upsets → TTF | proxy | Doha CAMS NO2 → TTF=F log ret (+) | S-0004 | −0.07 (−0.03) | −5d | 0.77 (1.0) | 390 | 56 / 54% / −0.23% / +0.06 | −0.46% → +0.19% | 0/2/2/3.9 | null |
| 8 Iraqi flaring = crude output → Brent | proxy | Basrah CAMS SO2 → BZ=F log ret (−) | S-0005 | −0.04 (−0.07) | +7d, +0.10 | 0.64 (1.0) | 390 | 28 / 50% / +0.33% / −0.61 | +0.76% → −0.42% | 0/2/2/2.1 | null — sign flips pre/war |
| 8 Ras Laffan sour-gas flaring → VG | proxy | Doha CAMS SO2 → VG log ret (+) | S-0006 | +0.01 (+0.01) | +7d, −0.11 | 0.62 (1.0) | 389 | 29 / 41% / −2.06% / −0.17 | −1.78% → −2.57% | 0/2/2/0.0 | null (VG is a 2025 IPO; very noisy) |
| 5 Snowpack/reservoir → hydro → gas price | proxy | US hydro MWh (monthly) → Henry Hub spot (−) | S-0007 | −0.09 (−0.15) | 0 mo | 0.66 | 15 | no trades (monthly) | — | 0/2/2/0.0 | **needs data / long history**: see mechanism check below |
| 5 Hydro → aluminium | proxy | US hydro MWh (monthly) → ALI=F log ret (−) | S-0008 | **−0.46 (−0.44)** | 0 mo | **0.002** | **15** | no trades (monthly) | — | 0/2/2/0.0 | suggestive but n=15 months; US hydro is not where smelters are (China/Canada/Norway) — needs global reservoir data |
| 4 Clouds → less solar → more gas burn → gas | proxy | Houston radiation → NG=F log ret (−) | S-0009 | −0.09 (−0.11) | 0d | 0.52 (1.0) | 388 | 36 / 42% / +0.28% / +0.38 | +0.72% → −0.48% | 0/2/2/1.8 | weak — sign correct contemporaneously, fails out of sample |
| 4 Clouds → utilities | proxy | Houston radiation → XLU log ret (+) | S-0010 | −0.03 (−0.07) | +9d | 0.92 (1.0) | 387 | 19 / 58% / −0.02% / +0.42 | +0.48% → −0.48% | 0/2/2/1.9 | null |
| 2 River height / barges → grains | weak proxy | Oklahoma City precip → ZW=F log ret (−) | S-0011 | +0.05 (−0.05) | −4d | 0.21 (1.0) | 387 | 34 / 35% / −0.07% / −0.76 | −0.50% → +0.52% | 0/2/2/2.8 | null — need Mississippi gauges + Corn Belt weather (wishlist) |
| 2 Plains heat stress → corn | weak proxy | Oklahoma City temp anomaly → ZC=F log ret (+) | S-0012 | +0.02 (−0.01) | −9d (reverse), +0.15 | 0.008 (0.17) | 387 | 54 / 50% / **+0.31%** / **+1.68** | **+0.35% → +0.25%** | 0/2/2/**7.6** | **interesting but fragile** — best correlation lag is reverse-causal (corn leads weather = noise); the z>1 heat rule is nevertheless positive in both halves |
| 6 Steel/cement thermal → copper | weak proxy | Houston CAMS SO2 → HG=F log ret (+) | S-0013 | −0.07 (−0.05) | −9d | 0.77 (1.0) | 390 | 45 / 53% / −0.28% / −0.29 | −0.51% → +0.08% | 0/2/2/3.8 | null — need plant-level TROPOMI/VIIRS (wishlist) |
| 6 Iranian industrial belt → FCX | weak proxy | Tehran CAMS SO2 → FCX log ret (+) | S-0014 | +0.08 (+0.05) | **+1d, +0.10** | **0.018** (0.38) | 389 | 58 / 52% / −0.15% / +0.23 | +0.02% → −0.37% | 0/2/2/1.8 | curiosity — significant 1-day lead before Bonferroni, but the rule does not beat the baseline |
| 3 Lithium evaporation ponds → lithium miners | **no** | — (needs Sentinel-2 pond colour/area) | — | | | | | | | | needs data |
| 7 Fishing-vessel behaviour → fishmeal/salmon | **no** | — (needs Global Fishing Watch AIS effort) | — | | | | | | | | needs data |
| 9 Wastewater chemistry → casinos/cruise | **no** | — (needs WastewaterSCAN / CDC NWSS) | — | | | | | | | | needs data |

### Mechanism check for #5 (outside the mission window)

The repo window starts 2025-03, so monthly hydro gives only 15 observations. Using the full
PUDL EIA-923 history (2008-01..2026-05, month-of-year de-seasonalised log anomalies, n=221):

| pair | r | Spearman | p |
|---|---|---|---|
| hydro generation anomaly vs **gas generation share** anomaly (same month) | **−0.25** | −0.28 | **0.0002** |
| hydro anomaly vs gas generation anomaly | −0.25 | −0.29 | 0.0002 |
| hydro anomaly vs Henry Hub monthly log price change (lag 0 / 1 / 2 months) | +0.01 / +0.05 / +0.00 | | 0.88 / 0.50 / 0.99 |
| Δhydro anomaly vs Henry Hub monthly log change (lag 0 / 1 / 2) | −0.08 / +0.10 / −0.01 | | 0.24 / 0.14 / 0.86 |

Reading: the *physical* half of the story is real and robust over 18 years — a wet/snowy year
displaces roughly a quarter-sigma of gas burn — but it does **not** pass through to the
Henry Hub price at monthly resolution (storage, exports and weather dominate). Reservoir/SNOTEL
data would let us test the *anticipation* (snowpack in March predicts hydro in June) rather
than the coincident relationship; that is the part a trader could act on.

## Top-3 demo-worthy findings (ranked)

1. **S-0002 — "Smell the ammonia plants": Houston SO2 spikes → long CF Industries.**
   `missions/runs/20260920-206-airquality-houston-cams-so2_x_finance-cf-log-return/viz.png`
   The Gulf Coast between Houston and Lake Charles hosts the largest ammonia/urea complexes
   in the western hemisphere (CF Donaldsonville, Yara/Nutrien Geismar, LSB) plus the LNG belt.
   Copernicus CAMS reanalysis SO2 over Houston is our crude "thermal signature" of how hard
   that belt is running. There is *no* linear relationship (r ≈ 0, perm p 0.82) — which is
   exactly why a correlation screen would miss it — but the tail rule "20-day SO2 z-score > 1
   at the close → long CF for 3 days" produced 35 non-overlapping trades, a 60% hit rate,
   +0.38% excess return per trade over the unconditional 3-day baseline, sharpe-like 1.9,
   and it kept working out of sample through the war (+0.44% pre-war → +0.28% war). Caveat
   for the demo: heuristic actionability 8.6 is the *best* number in the table; 35 trades
   is thin, and SO2 in a reanalysis is a regional, not plant-level, signal. Upgrade path:
   Sentinel-5P SO2/NO2 at Donaldsonville coordinates + VIIRS Nightfire (wishlist §3–4).

2. **S-0007/S-0008 + mechanism check — "Snowmelt is the enemy of gas burn, but the market
   already knows."**
   `missions/runs/20260920-211-utility-generation-hydro-mwh_x_finance-fred-dhhngsp/viz.png`
   `missions/runs/20260920-212-utility-generation-hydro-mwh_x_finance-ali-f-log-return/viz.png`
   Over 18 years of EIA-923 data, months with anomalously high US hydro output have a
   significantly lower gas generation share (r −0.25, p 0.0002, n 221): the physical
   displacement is real. Yet the same hydro anomaly has zero relationship with Henry Hub
   monthly price changes at lags 0–2 months, and in the 2025-26 window it correlates with
   aluminium returns (r −0.46, n 15, perm p 0.002) only because both share the 2025 seasonal
   path. It is a clean negative-result narrative for the Sherlock theme ("the observable is
   real, the edge is not") and a set-up for the wishlist: what *would* be tradeable is
   snowpack (SNOTEL SWE) in March predicting hydro in June, i.e. the anticipation, not the
   coincidence.

3. **S-0012 — "Hot Plains, hot corn": Oklahoma City heat anomaly → long corn.**
   `missions/runs/20260920-216-weather-oklahoma-city-temp-anomaly_x_finance-zc-f-log-return/viz.png`
   With no Corn Belt station in the weather set, Oklahoma City is the closest we have to a
   heat-dome sentinel. The linear scan is honest noise (the best correlation is at a
   reverse-causal −9 day lag, i.e. corn "predicting" weather), but the z>1 heat rule with a
   1-day hold took 54 trades, +0.31% excess per trade, sharpe-like 1.7, and was positive both
   pre-war (+0.35%) and during the war (+0.25%, 22 trades, 55% hit). Present it as a hypothesis
   worth re-running with Des Moines / Peoria / Champaign temperature and USGS Mississippi
   stage (wishlist §1–2), not as a result.

Runner-up: **S-0014** Tehran SO2 leads FCX by one day (r +0.10, perm p 0.018 before
Bonferroni) — a fun "Iranian industrial belt" curiosity that fails the trade test.

## Caveats (carry into any slide)

* Heuristic brain / heuristic judge: validity is 0 for every mission because no Jev key is
  configured on the research box; the informative fields are perm p, the trade stats and the
  pre/war split.
* Daily closes, no costs/slippage; the war is a common cause of many signals and targets.
* Monthly PUDL series have `max_lag = 0 months` under the Round 2 lag clip (3..10 days), so
  S-0007/S-0008 are coincident tests only.
* CAMS is a model reanalysis over a city box, not a plant-level observation; it is the proxy,
  not the Sherlock observable itself.
