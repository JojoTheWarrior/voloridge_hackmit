# M20260920-6c2c2e

| Field | Value |
|---|---|
| Mission id | `M20260920-6c2c2e` |
| Folder | `20260920-126-finance-ng-f-log-return_x_airquality-houston-pm25` |
| Indicators | `finance.NG=F.log_return` × `airquality.houston.pm25` |
| n_obs | 40 |
| r | 0.22614872806386285 |
| Best lag | 0 (days) |
| perm_p | 0.4930139720558882 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 1.76, 'interestingness': 3.8, 'unexpectedness': 1.66, 'supported_prob': 0.02, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.NG=F.log_return` (configured analysis window); `airquality.houston.pm25` (downloaded observations) |

## Research note: Henry Hub gas returns vs Houston PM2.5 anomaly (war window)

**1. Verdict.** Not supported: the same-day Pearson r of 0.23 (n=40) is not distinguishable from zero (p=0.16; permutation p=0.49; Bonferroni-adjusted p=1.0).

**2. What the data shows.** Over 2026-03-02 to 2026-09-15 there are only 40 overlapping observations (weekly-ish alignment of NG=F log returns with the Houston PM2.5 seasonal anomaly). Pearson r=0.23, Spearman r=0.12 (p=0.47) – the gap between the two suggests a few outlier weeks drive the linear estimate. Scanning lags of -3..+3 days (7 tests), the best lag is 0 with identical r=0.23; no lead/lag structure emerges. Sign matches the expected positive direction, but with perm p≈0.49 that is a coin flip. No pre/post or event-study statistics were computed in this pair mode.

**3. Confounders and caveats.** (a) The indicator is a proxy for a proxy: Henry Hub returns reflect national gas balances, storage reports, LNG export disruptions and Hormuz-driven energy repricing far more than Texas power demand; the intended EIA-930 regional demand series was never used. (b) Houston PM2.5 is dominated by Gulf meteorology (stagnation, Saharan dust, wildfire smoke, sea-breeze recirculation) and local petrochemical activity; the seasonal anomaly transform only partly removes this. (c) Daily returns are near-white-noise while PM2.5 anomalies are autocorrelated; mixing frequencies inflates apparent correlations. (d) The war window itself (Hormuz closure, Brent peak, tanker war) is a common shock to gas prices and refinery/petrochemical throughput. (e) n=40 with 7 lag tests gives very low power.

**4. Follow-up.** Rerun with actual PUDL/EIA-930 ERCOT hourly demand aggregated to daily degree-day-adjusted anomalies against Houston PM2.5, adding Open-Meteo wind speed and boundary-layer proxies as controls, with a 2025 pre-war window as a null comparison.
