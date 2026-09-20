# R2-0187

| Field | Value |
|---|---|
| Mission id | `R2-0187` |
| Folder | `20260920-272-gdelt-gkg-hormuz-share_x_finance-uso-log-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.USO.log_return` |
| n_obs | 390 |
| r | 0.09214498042099561 |
| Best lag | 7 (days) |
| perm_p | 0.0658682634730539 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.2, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.USO.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.09214498042099561, n=390).

The best tested lag was 7 days with r=-0.21693352502792895.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long USO**, hold 7d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> long USO next session
- Exit: close after 7 trading days (no overlapping entries)
- n_trades=3 hit_rate=0.6666666666666666 avg_return=0.054389711053939714 excess=0.027153306670189233 sharpe_like=1.7996241984096237 max_dd=-0.004974813539378009
- OOS (war period): n=3 hit=0.6666666666666666 avg=0.054389711053939714
- Actionability: 1.2
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
