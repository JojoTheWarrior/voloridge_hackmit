# M20260920-eb02f2

| Field | Value |
|---|---|
| Mission id | `M20260920-eb02f2` |
| Folder | `20260920-042-weather-houston-temp-mean_x_utility-us-demand-peak-mwh` |
| Indicators | `weather.houston.temp_mean` × `utility.us.demand_peak_mwh` |
| n_obs | 555 |
| r | 0.5041912323441746 |
| Best lag | 0 (days) |
| perm_p | 0.01996007984031936 |
| Bonferroni | 0.01996007984031936 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 7.2568666801552, 'interestingness': 4.0167649293766985, 'unexpectedness': 4.520956161720873, 'supported_prob': 1.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.temp_mean` (configured analysis window); `utility.us.demand_peak_mwh` (configured analysis window) |

**Verdict:** supported (Pearson r=0.5041912323441746, n=555).

The best tested lag was 0 days with r=0.5041912323441743.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
