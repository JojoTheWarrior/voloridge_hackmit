# M20260920-648242

| Field | Value |
|---|---|
| Mission id | `M20260920-648242` |
| Folder | `20260920-074-finance-vix-close_x_finance-bz-f-close` |
| Indicators | `finance.^VIX.close` × `finance.BZ=F.close` |
| n_obs | 140 |
| r | 0.3700956087977466 |
| Best lag | 0 (days) |
| perm_p | 0.029940119760479042 |
| Bonferroni | 0.32934131736526945 |
| pre/post Δr | None |
| Fisher p | None |
| Scores | {'validity': 6.02, 'interestingness': 1.76, 'unexpectedness': 3.44, 'supported_prob': 0.74, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.^VIX.close` (configured analysis window); `finance.BZ=F.close` (configured analysis window) |

**Verdict:** supported (Pearson r=0.3700956087977466, n=140).

The best tested lag was 0 days with r=0.37009560879774644.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
