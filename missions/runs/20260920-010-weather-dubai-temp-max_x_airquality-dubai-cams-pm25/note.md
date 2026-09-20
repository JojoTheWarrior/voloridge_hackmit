# M20260920-3578d6

| Field | Value |
|---|---|
| Mission id | `M20260920-3578d6` |
| Folder | `20260920-010-weather-dubai-temp-max_x_airquality-dubai-cams-pm25` |
| Indicators | `weather.dubai.temp_max` × `airquality.dubai.cams_pm25` |
| n_obs | 564 |
| r | 0.28459184471163534 |
| Best lag | -1 (days) |
| perm_p | 0.23552894211576847 |
| Bonferroni | 1.0 |
| pre/post Δr | 0.4704222110628845 |
| Fisher p | 2.036207340861178e-09 |
| Scores | {'validity': 2.62, 'interestingness': 7.26, 'unexpectedness': 6.28, 'supported_prob': 0.95, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.dubai.temp_max` (configured analysis window); `airquality.dubai.cams_pm25` (2025-03..2026-09 archive window) |

**Verdict:** supported (Pearson r=0.28459184471163534, n=564).

The best tested lag was -1 days with r=0.2924919810844128.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
