# M20260920-e1a73e

| Field | Value |
|---|---|
| Mission id | `M20260920-e1a73e` |
| Folder | `20260920-029-utility-us-demand-anomaly_x_finance-fred-dhhngsp` |
| Indicators | `utility.us.demand_anomaly` × `finance.fred.DHHNGSP` |
| n_obs | 127 |
| r | 0.0077213705945525105 |
| Best lag | -1 (days) |
| perm_p | 0.5968063872255489 |
| Bonferroni | 1.0 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 0.02, 'interestingness': 2.86, 'unexpectedness': 0.82, 'supported_prob': 0.03, 'judge_model': 'jev-1.13.0'} |
| Data sources | `utility.us.demand_anomaly` (configured analysis window); `finance.fred.DHHNGSP` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0077213705945525105, n=127).

The best tested lag was -1 days with r=0.04550909755152888.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
