# R2-0059

| Field | Value |
|---|---|
| Mission id | `R2-0059` |
| Folder | `20260920-172-gdelt-gkg-ceasefire-share_x_finance-ual-log-return` |
| Indicators | `gdelt.gkg.ceasefire_share` × `finance.UAL.log_return` |
| n_obs | 390 |
| r | 0.052317265610215935 |
| Best lag | -3 (days) |
| perm_p | 0.2654690618762475 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.32, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.ceasefire_share` (configured analysis window); `finance.UAL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.052317265610215935, n=390).

The best tested lag was -3 days with r=0.10032165890871918.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long UAL**, hold 1d
- Entry: gdelt.gkg.ceasefire_share rolling_zscore_20d > 1 at close -> long UAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.4827586206896552 avg_return=0.002386381948344009 excess=0.0009262828938009385 sharpe_like=0.49610941662215324 max_dd=-0.08542612466978783
- OOS (war period): n=14 hit=0.35714285714285715 avg=-0.0025939960888938162
- Actionability: 3.32
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
