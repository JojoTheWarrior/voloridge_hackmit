# R2-0153

| Field | Value |
|---|---|
| Mission id | `R2-0153` |
| Folder | `20260920-249-finance-ratio-ttf-henryhub_x_finance-cf-log-return` |
| Indicators | `finance.ratio.ttf_henryhub` × `finance.CF.log_return` |
| n_obs | 389 |
| r | 0.13259754167655427 |
| Best lag | 0 (days) |
| perm_p | 0.16766467065868262 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 0.71, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.ratio.ttf_henryhub` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.13259754167655427, n=389).

The best tested lag was 0 days with r=0.13259754167655424.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 1d
- Entry: finance.ratio.ttf_henryhub rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=44 hit_rate=0.5227272727272727 avg_return=-0.001212931796203967 excess=-0.002836871490850724 sharpe_like=-0.35594117235269146 max_dd=-0.16922189067265903
- OOS (war period): n=15 hit=0.4666666666666667 avg=-0.002112152769646395
- Actionability: 0.71
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
