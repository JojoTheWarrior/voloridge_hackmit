# R2-0018

| Field | Value |
|---|---|
| Mission id | `R2-0018` |
| Folder | `20260920-145-finance-bz-f-close_x_finance-bz-f-log-return` |
| Indicators | `finance.BZ=F.close` × `finance.BZ=F.log_return` |
| n_obs | 390 |
| r | 1.0 |
| Best lag | 0 (days) |
| perm_p | 0.05389221556886228 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 3.1, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.BZ=F.close` (configured analysis window); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=1.0, n=390).

The best tested lag was 0 days with r=0.9999999999999999.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short BZ=F**, hold 1d
- Entry: finance.BZ=F.close rolling_zscore_20d > 1 at close -> short BZ=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=50 hit_rate=0.46 avg_return=-0.00304386438295712 excess=-0.001583726746394833 sharpe_like=-0.6798670350051252 max_dd=-0.2629021995395864
- OOS (war period): n=16 hit=0.375 avg=-0.0021847842260677985
- Actionability: 3.1
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
