# R2-0007

| Field | Value |
|---|---|
| Mission id | `R2-0007` |
| Folder | `20260920-138-gdelt-gkg-ceasefire-share_x_finance-ratio-tankers-xle` |
| Indicators | `gdelt.gkg.ceasefire_share` × `finance.ratio.tankers_xle` |
| n_obs | 389 |
| r | 0.007829248136226903 |
| Best lag | -5 (days) |
| perm_p | 0.40119760479041916 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 1.17, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.ceasefire_share` (configured analysis window); `finance.ratio.tankers_xle` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.007829248136226903, n=389).

The best tested lag was -5 days with r=0.08813556374713515.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:tankers_xle**, hold 1d
- Entry: gdelt.gkg.ceasefire_share rolling_zscore_20d > 1 at close -> short ratio:tankers_xle next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.0 avg_return=-0.7503249648340116 excess=-0.026548206662604157 sharpe_like=-21.40215782495808 max_dd=-1.0000000000000009
- OOS (war period): n=14 hit=0.0 avg=-0.8908049033922697
- Actionability: 1.17
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
