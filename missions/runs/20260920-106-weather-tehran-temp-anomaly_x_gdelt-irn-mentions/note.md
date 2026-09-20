# M20260920-22459e

| Field | Value |
|---|---|
| Mission id | `M20260920-22459e` |
| Folder | `20260920-106-weather-tehran-temp-anomaly_x_gdelt-irn-mentions` |
| Indicators | `weather.tehran.temp_anomaly` × `gdelt.irn.mentions` |
| n_obs | 564 |
| r | -0.06815122828033127 |
| Best lag | -7 (days) |
| perm_p | 0.6387225548902196 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.24, 'interestingness': 3.26, 'unexpectedness': 6.32, 'supported_prob': 0.01, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.tehran.temp_anomaly` (configured analysis window); `gdelt.irn.mentions` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.06815122828033127, n=564).

The best tested lag was -7 days with r=-0.15879504571219516.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
