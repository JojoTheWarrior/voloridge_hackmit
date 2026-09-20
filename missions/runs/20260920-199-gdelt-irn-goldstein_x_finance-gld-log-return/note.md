# R2-0100

| Field | Value |
|---|---|
| Mission id | `R2-0100` |
| Folder | `20260920-199-gdelt-irn-goldstein_x_finance-gld-log-return` |
| Indicators | `gdelt.irn.goldstein` × `finance.GLD.log_return` |
| n_obs | 390 |
| r | 0.03394952351303365 |
| Best lag | -5 (days) |
| perm_p | 0.6646706586826348 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 2.62, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.irn.goldstein` (configured analysis window); `finance.GLD.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.03394952351303365, n=390).

The best tested lag was -5 days with r=0.08749748895834233.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long GLD**, hold 1d
- Entry: gdelt.irn.goldstein rolling_zscore_20d > 1 at close -> long GLD next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.5925925925925926 avg_return=0.0008643432556606818 excess=-0.00034445721341673345 sharpe_like=0.2877380799506196 max_dd=-0.14135195395202116
- OOS (war period): n=18 hit=0.3888888888888889 avg=-0.007434361250057525
- Actionability: 2.62
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
