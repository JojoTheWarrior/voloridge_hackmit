# R2-0105

| Field | Value |
|---|---|
| Mission id | `R2-0105` |
| Folder | `20260920-204-gdelt-omn-events_x_finance-bz-f-log-return` |
| Indicators | `gdelt.omn.events` × `finance.BZ=F.log_return` |
| n_obs | 391 |
| r | 0.14053741238675188 |
| Best lag | 2 (days) |
| perm_p | 0.08383233532934131 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.74, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.omn.events` (configured analysis window); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.14053741238675188, n=391).

The best tested lag was 2 days with r=0.172470775428861.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long BZ=F**, hold 2d
- Entry: gdelt.omn.events rolling_zscore_20d > 1 at close -> long BZ=F next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=48 hit_rate=0.6666666666666666 avg_return=0.010752719591234082 excess=0.007724923967650822 sharpe_like=2.3634678850010826 max_dd=-0.1251952176886575
- OOS (war period): n=14 hit=0.5714285714285714 avg=-0.00046999595495436246
- Actionability: 6.74
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
