# M20260920-595055

| Field | Value |
|---|---|
| Mission id | `M20260920-595055` |
| Folder | `20260920-018-weather-houston-temp-anomaly_x_finance-fred-dhhngsp` |
| Indicators | `weather.houston.temp_anomaly` × `finance.fred.DHHNGSP` |
| n_obs | 366 |
| r | 0.17359562015469254 |
| Best lag | 1 (days) |
| perm_p | 0.05588822355289421 |
| Bonferroni | 0.8383233532934131 |
| pre/post Δr | -0.22809154273268806 |
| Fisher p | 0.035624048228528944 |
| Scores | {'validity': 4.42, 'interestingness': 4.56, 'unexpectedness': 9.3, 'supported_prob': 0.06, 'judge_model': 'jev-1.13.0'} |
| Data sources | `weather.houston.temp_anomaly` (configured analysis window); `finance.fred.DHHNGSP` (configured analysis window) |

**Verdict:** supported (Pearson r=0.17359562015469254, n=366).

The best tested lag was 1 days with r=0.1865702335431316.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
