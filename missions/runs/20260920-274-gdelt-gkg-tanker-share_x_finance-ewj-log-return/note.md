# R2-0188

| Field | Value |
|---|---|
| Mission id | `R2-0188` |
| Folder | `20260920-274-gdelt-gkg-tanker-share_x_finance-ewj-log-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.EWJ.log_return` |
| n_obs | 390 |
| r | 0.008032941002348167 |
| Best lag | -1 (days) |
| perm_p | 0.6387225548902196 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.24, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.EWJ.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.008032941002348167, n=390).

The best tested lag was -1 days with r=-0.06780649619198692.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long EWJ**, hold 1d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> long EWJ next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=28 hit_rate=0.6428571428571429 avg_return=0.0021280921658166085 excess=0.001133362313490421 sharpe_like=1.0041687804644164 max_dd=-0.039381094792827365
- OOS (war period): n=11 hit=0.5454545454545454 avg=-0.00041290843888895016
- Actionability: 5.24
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
