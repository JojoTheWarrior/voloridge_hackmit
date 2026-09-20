# M20260920-af4c14

| Field | Value |
|---|---|
| Mission id | `M20260920-af4c14` |
| Folder | `20260920-072-finance-bz-f-log-return_x_finance-gspc-log-return` |
| Indicators | `finance.BZ=F.log_return` × `finance.^GSPC.log_return` |
| n_obs | 390 |
| r | -0.07426659773764337 |
| Best lag | 4 (days) |
| perm_p | 0.08982035928143713 |
| Bonferroni | 0.9880239520958084 |
| pre/post Δr | -0.70405635085024 |
| Fisher p | 2.6812893533773096e-12 |
| Scores | {'validity': 4.18, 'interestingness': 4.7, 'unexpectedness': 4.98, 'supported_prob': 0.95, 'judge_model': 'jev-1.13.0'} |
| Data sources | `finance.BZ=F.log_return` (configured analysis window); `finance.^GSPC.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.07426659773764337, n=390).

The best tested lag was 4 days with r=-0.13400150043324494.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.
