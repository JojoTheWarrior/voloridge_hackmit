# R2-0037

| Field | Value |
|---|---|
| Mission id | `R2-0037` |
| Folder | `20260920-158-finance-ttf-f-log-return_prepost` |
| Indicators | `finance.TTF=F.log_return` |
| n_obs | 391 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.01996007984031936 |
| Bonferroni | 0.01996007984031936 |
| pre/post mean Δ | 0.00781364344009836 |
| Welch p | 0.11933906581292678 |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** not supported (mean change=0.00781364344009836, n=391).

The post-boundary mean changed by 0.00781364344009836; Welch p=0.11933906581292678.

This difference is descriptive, not causal; seasonality, common shocks, and boundary selection remain possible confounders.
