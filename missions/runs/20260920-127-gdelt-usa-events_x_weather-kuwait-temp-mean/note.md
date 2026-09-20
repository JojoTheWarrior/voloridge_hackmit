# M20260920-724b33

| Field | Value |
|---|---|
| Mission id | `M20260920-724b33` |
| Folder | `20260920-127-gdelt-usa-events_x_weather-kuwait-temp-mean` |
| Indicators | `gdelt.usa.events` × `weather.kuwait.temp_mean` |
| n_obs | 564 |
| r | -0.1531018619478953 |
| Best lag | 0 (days) |
| perm_p | 0.0658682634730539 |
| Bonferroni | 0.0658682634730539 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 4.0, 'interestingness': 3.84, 'unexpectedness': 5.36, 'supported_prob': 0.04, 'judge_model': 'jev-1.13.0'} |
| Data sources | `gdelt.usa.events` (configured analysis window); `weather.kuwait.temp_mean` (configured analysis window) |

## Research note: Gulf dust days vs. GDELT airstrike reporting

**1) Verdict.** Inconclusive for the stated hypothesis — the executed pair (GDELT *USA* event counts vs. *Kuwait mean temperature*) does not measure sandstorms/visibility or airstrikes; the pair itself shows only a weak negative association (Pearson r = −0.15, permutation p = 0.066).

**2) What the data shows.** n = 564 daily observations (2025-03-01 → 2026-09-15), level-on-level, lag 0 only. Pearson r = −0.153 (p = 0.0003), Spearman r = −0.141 (p = 0.0008); best lag = 0 by construction (max_lag 0, 1 lag tested, Bonferroni p = 0.066). The block-permutation p (0.066) is ~250× larger than the parametric p, indicating the asymptotic p-values are inflated by autocorrelation/trend and the effect is not robust. No pre/post-war split or event study was run. Sign is negative as expected, but the ~2% shared variance is practically negligible.

**3) Confounders and caveats.** (a) Proxy mismatch: temperature is not a dust/visibility indicator (ISD visibility or OpenAQ PM10 would be), and `gdelt.usa.events` is total US-coded events, not airstrike (CAMEO 19x) counts in Iraq/Kuwait. (b) Strong seasonality in Kuwait temperature vs. war-driven regime shifts in GDELT volume (Feb–Apr 2026 surge fell in cooler months) can manufacture a negative correlation with no daily mechanism. (c) GDELT counts are non-stationary and media-attention driven; levels without differencing invite spurious correlation. (d) Single lag, single window — no out-of-sample check.

**4) Follow-up.** Re-run with `weather.kuwait|iraq.visibility_min` or `openaq.baghdad.pm10` vs. GDELT CAMEO 190–195 events geolocated to Iraq/Iran, first-differenced or seasonally adjusted, restricted to the 2026-02-28→2026-04-07 open-war window, with lags 0–3 days and a shuffled-date null control.
