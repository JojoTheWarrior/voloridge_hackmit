# M20260920-f6c46e

| Field | Value |
|---|---|
| Mission id | `M20260920-f6c46e` |
| Folder | `20260920-019-weather-nyc-jfk-temp-anomaly_x_finance-fred-dhhngsp` |
| Indicators | `weather.nyc_jfk.temp_anomaly` × `finance.fred.DHHNGSP` |
| n_obs | 132 |
| r | 0.019408996367924484 |
| Best lag | 4 (days) |
| perm_p | 0.1437125748502994 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 3.84, 'interestingness': 3.98, 'unexpectedness': 2.7, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.nyc_jfk.temp_anomaly` (configured analysis window); `finance.fred.DHHNGSP` (configured analysis window) |

**Verdict:** supported (Pearson r=0.019408996367924484, n=132).

The best tested lag was 4 days with r=-0.18030389026122762.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
