# R2-0084

| Field | Value |
|---|---|
| Mission id | `R2-0084` |
| Folder | `20260920-189-gdelt-gkg-drone-share_x_finance-noc-log-return` |
| Indicators | `gdelt.gkg.drone_share` × `finance.NOC.log_return` |
| n_obs | 390 |
| r | -0.03969085262800123 |
| Best lag | 6 (days) |
| perm_p | 0.3652694610778443 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 4.82, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.drone_share` (configured analysis window); `finance.NOC.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.03969085262800123, n=390).

The best tested lag was 6 days with r=-0.10347483848542273.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NOC**, hold 6d
- Entry: gdelt.gkg.drone_share rolling_zscore_20d > 1 at close -> long NOC next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=19 hit_rate=0.47368421052631576 avg_return=0.0034424608001277137 excess=0.0012700389229941171 sharpe_like=0.3235777424685843 max_dd=-0.16473166371006132
- OOS (war period): n=5 hit=0.4 avg=0.010651597653044242
- Actionability: 4.82
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
