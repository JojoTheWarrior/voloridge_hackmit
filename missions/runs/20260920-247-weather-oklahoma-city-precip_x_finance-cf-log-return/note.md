# R2-0149

| Field | Value |
|---|---|
| Mission id | `R2-0149` |
| Folder | `20260920-247-weather-oklahoma-city-precip_x_finance-cf-log-return` |
| Indicators | `weather.oklahoma_city.precip` × `finance.CF.log_return` |
| n_obs | 387 |
| r | -0.012301493783556413 |
| Best lag | 2 (days) |
| perm_p | 0.846307385229541 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.37, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.oklahoma_city.precip` (configured analysis window); `finance.CF.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.012301493783556413, n=387).

The best tested lag was 2 days with r=-0.07842718047097641.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long CF**, hold 2d
- Entry: weather.oklahoma_city.precip rolling_zscore_20d > 1 at close -> long CF next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.5172413793103449 avg_return=0.0003414728954210838 excess=-0.0031385666575636678 sharpe_like=0.046456906334684606 max_dd=-0.17360370563353267
- OOS (war period): n=14 hit=0.5714285714285714 avg=0.00484701546503215
- Actionability: 3.37
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
