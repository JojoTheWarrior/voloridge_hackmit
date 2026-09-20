# R2-0088

| Field | Value |
|---|---|
| Mission id | `R2-0088` |
| Folder | `20260920-193-gdelt-gkg-hormuz-share_x_finance-inda-log-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.INDA.log_return` |
| n_obs | 390 |
| r | -0.06162642176754103 |
| Best lag | 7 (days) |
| perm_p | 0.01996007984031936 |
| Bonferroni | 0.41916167664670656 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.2, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.INDA.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.06162642176754103, n=390).

The best tested lag was 7 days with r=0.2241889928615449.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short INDA**, hold 7d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> short INDA next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=3 hit_rate=0.3333333333333333 avg_return=0.0040567808536953924 excess=0.008618041802066878 sharpe_like=0.6506997540074696 max_dd=-0.007132778636271597
- OOS (war period): n=3 hit=0.3333333333333333 avg=0.0040567808536953924
- Actionability: 1.2
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
