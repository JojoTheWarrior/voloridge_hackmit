# R2-0134

| Field | Value |
|---|---|
| Mission id | `R2-0134` |
| Folder | `20260920-235-finance-ng-f-log-return_x_finance-xlu-log-return` |
| Indicators | `finance.NG=F.log_return` × `finance.XLU.log_return` |
| n_obs | 390 |
| r | 0.038089175053728115 |
| Best lag | 1 (days) |
| perm_p | 0.7365269461077845 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 0, 'unexpectedness': 0, 'actionability': 4.55, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `finance.NG=F.log_return` (configured analysis window); `finance.XLU.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.038089175053728115, n=390).

The best tested lag was 1 days with r=-0.08875999575569728.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long XLU**, hold 1d
- Entry: finance.NG=F.log_return rolling_zscore_20d > 1 at close -> long XLU next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=41 hit_rate=0.5121951219512195 avg_return=-0.0009337527329825924 excess=-0.001091607157778045 sharpe_like=-0.6193359110815115 max_dd=-0.08463069485654162
- OOS (war period): n=15 hit=0.4666666666666667 avg=0.0007077280888627542
- Actionability: 4.55
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
