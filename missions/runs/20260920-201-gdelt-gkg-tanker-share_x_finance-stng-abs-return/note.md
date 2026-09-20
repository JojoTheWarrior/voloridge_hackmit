# R2-0102

| Field | Value |
|---|---|
| Mission id | `R2-0102` |
| Folder | `20260920-201-gdelt-gkg-tanker-share_x_finance-stng-abs-return` |
| Indicators | `gdelt.gkg.tanker_share` × `finance.STNG.abs_return` |
| n_obs | 390 |
| r | -0.07183500734380478 |
| Best lag | -4 (days) |
| perm_p | 0.5369261477045908 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 10.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.tanker_share` (configured analysis window); `finance.STNG.abs_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.07183500734380478, n=390).

The best tested lag was -4 days with r=-0.10681087911243572.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long STNG**, hold 1d
- Entry: gdelt.gkg.tanker_share rolling_zscore_20d > 1 at close -> long STNG next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=28 hit_rate=1.0 avg_return=0.019848523812616727 excess=0.0010022007883234776 sharpe_like=5.909361327849122 max_dd=0.0
- OOS (war period): n=11 hit=1.0 avg=0.021738617744537538
- Actionability: 10.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
