# R2-0145

| Field | Value |
|---|---|
| Mission id | `R2-0145` |
| Folder | `20260920-244-gdelt-gkg-fertilizer-share_x_finance-cf-abs-return` |
| Indicators | `gdelt.gkg.fertilizer_share` × `finance.CF.abs_return` |
| n_obs | 390 |
| r | 0.21815372622398654 |
| Best lag | -6 (days) |
| perm_p | 0.11776447105788423 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 10.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `gdelt.gkg.fertilizer_share` (configured analysis window); `finance.CF.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.21815372622398654, n=390).

The best tested lag was -6 days with r=0.28752995257764963.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 1d
- Entry: gdelt.gkg.fertilizer_share rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=45 hit_rate=1.0 avg_return=0.021809824189155183 excess=0.003337094290840479 sharpe_like=6.672254513351088 max_dd=0.0
- OOS (war period): n=20 hit=1.0 avg=0.02831757897846261
- Actionability: 10.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
