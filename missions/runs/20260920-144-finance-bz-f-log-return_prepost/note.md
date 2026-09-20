# R2-0018

| Field | Value |
|---|---|
| Mission id | `R2-0018` |
| Folder | `20260920-144-finance-bz-f-log-return_prepost` |
| Indicators | `finance.BZ=F.log_return` |
| n_obs | 391 |
| r |  |
| Best lag | n/a (days) |
| perm_p | 0.2754491017964072 |
| Bonferroni | 0.2754491017964072 |
| pre/post mean Δ | 0.0026085029067515956 |
| Welch p | 0.5004224277164884 |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (mean change=0.0026085029067515956, n=391).

The post-boundary mean changed by 0.0026085029067515956; Welch p=0.5004224277164884.

This difference is descriptive, not causal; seasonality, common shocks, and boundary selection remain possible confounders.
