# M20260920-f1a810

| Field | Value |
|---|---|
| Mission id | `M20260920-f1a810` |
| Folder | `20260920-009-weather-tehran-wind-max_x_airquality-tehran-cams-pm25` |
| Indicators | `weather.tehran.wind_max` × `airquality.tehran.cams_pm25` |
| n_obs | 200 |
| r | -0.05604008556424099 |
| Best lag | 0 (days) |
| perm_p | 0.7105788423153693 |
| Bonferroni | 0.7105788423153693 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.02, 'interestingness': 2.72, 'unexpectedness': 0.54, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.tehran.wind_max` (configured analysis window); `airquality.tehran.cams_pm25` (2025-03..2026-09 archive window) |

**Verdict:** supported (Pearson r=-0.05604008556424099, n=200).

The best tested lag was 0 days with r=-0.05604008556424103.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
