# R2-0101

| Field | Value |
|---|---|
| Mission id | `R2-0101` |
| Folder | `20260920-200-gdelt-gkg-hormuz-share_x_finance-fro-abs-return` |
| Indicators | `gdelt.gkg.hormuz_share` × `finance.FRO.abs_return` |
| n_obs | 390 |
| r | -0.016678534760574328 |
| Best lag | -9 (days) |
| perm_p | 0.5209580838323353 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 9.1, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.hormuz_share` (configured analysis window); `finance.FRO.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=-0.016678534760574328, n=390).

The best tested lag was -9 days with r=0.09895056388245384.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long FRO**, hold 1d
- Entry: gdelt.gkg.hormuz_share rolling_zscore_20d > 1 at close -> long FRO next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=5 hit_rate=1.0 avg_return=0.020156825811004798 excess=0.0005402047556556343 sharpe_like=2.993954675270374 max_dd=0.0
- OOS (war period): n=5 hit=1.0 avg=0.020156825811004798
- Actionability: 9.1
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
