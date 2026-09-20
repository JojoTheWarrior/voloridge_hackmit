# M20260920-c7ca8d

| Field | Value |
|---|---|
| Mission id | `M20260920-c7ca8d` |
| Folder | `20260920-030-finance-fred-dcoilbrenteu_x_utility-us-demand-mwh` |
| Indicators | `finance.fred.DCOILBRENTEU` × `utility.us.demand_mwh` |
| n_obs | 382 |
| r | 0.012372654858887912 |
| Best lag | 28 (days) |
| perm_p | 0.5848303393213573 |
| Bonferroni | 1.0 |
| pre/post Δr | -0.11219352341100149 |
| Fisher p | 0.30124683478168857 |
| Scores | {'validity': 0.12, 'interestingness': 4.96, 'unexpectedness': 6.36, 'supported_prob': 0.04, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.fred.DCOILBRENTEU` (configured analysis window); `utility.us.demand_mwh` (configured analysis window) |

**Verdict:** supported (Pearson r=0.012372654858887912, n=382).

The best tested lag was 28 days with r=0.08002912161897169.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
