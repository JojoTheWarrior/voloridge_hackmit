# R2-0163

| Field | Value |
|---|---|
| Mission id | `R2-0163` |
| Folder | `20260920-261-gdelt-gkg-drone-share_x_finance-dal-log-return` |
| Indicators | `gdelt.gkg.drone_share` × `finance.DAL.log_return` |
| n_obs | 390 |
| r | -0.02530374111271539 |
| Best lag | -1 (days) |
| perm_p | 0.7305389221556886 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 6.19, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.drone_share` (configured analysis window); `finance.DAL.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.02530374111271539, n=390).

The best tested lag was -1 days with r=-0.07177498386028368.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short DAL**, hold 1d
- Entry: gdelt.gkg.drone_share rolling_zscore_20d > 1 at close -> short DAL next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=30 hit_rate=0.5 avg_return=-0.0005927428960530631 excess=0.0010240085607617008 sharpe_like=-0.15053124318504033 max_dd=-0.12850284002906642
- OOS (war period): n=10 hit=0.5 avg=0.005985629185647623
- Actionability: 6.19
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
