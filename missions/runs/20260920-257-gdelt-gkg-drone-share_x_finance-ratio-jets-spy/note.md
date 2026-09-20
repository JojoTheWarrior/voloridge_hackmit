# R2-0164

| Field | Value |
|---|---|
| Mission id | `R2-0164` |
| Folder | `20260920-257-gdelt-gkg-drone-share_x_finance-ratio-jets-spy` |
| Indicators | `gdelt.gkg.drone_share` × `finance.ratio.jets_spy` |
| n_obs | 389 |
| r | -0.1154800413238529 |
| Best lag | -1 (days) |
| perm_p | 0.11976047904191617 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 8.16, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.drone_share` (configured analysis window); `finance.ratio.jets_spy` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.1154800413238529, n=389).

The best tested lag was -1 days with r=-0.12629043860919026.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **short ratio:jets_spy**, hold 1d
- Entry: gdelt.gkg.drone_share rolling_zscore_20d > 1 at close -> short ratio:jets_spy next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=30 hit_rate=0.6333333333333333 avg_return=0.0023876608871242987 excess=0.002381983655779008 sharpe_like=0.9569990375488565 max_dd=-0.07910206765945238
- OOS (war period): n=10 hit=0.9 avg=0.010335542023397681
- Actionability: 8.16
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
