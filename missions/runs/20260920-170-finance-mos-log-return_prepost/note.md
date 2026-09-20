# R2-0056

| Field | Value |
|---|---|
| Mission id | `R2-0056` |
| Folder | `20260920-170-finance-mos-log-return_prepost` |
| Indicators | `finance.MOS.log_return` |
| n_obs | 390 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.7425149700598802 |
| Bonferroni | 0.7425149700598802 |
| pre/post mean Δ | -0.0015257313632896345 |
| Welch p | 0.6138163812116979 |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.MOS.log_return` (configured analysis window) |

**Verdict:** supported (mean change=-0.0015257313632896345, n=390).

The post-boundary mean changed by -0.0015257313632896345; Welch p=0.6138163812116979.

This difference is descriptive, not causal; seasonality, common shocks, and boundary selection remain possible confounders.
