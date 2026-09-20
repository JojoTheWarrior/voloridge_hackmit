# R2-0130

| Field | Value |
|---|---|
| Mission id | `R2-0130` |
| Folder | `20260920-233-weather-houston-temp-anomaly_x_finance-ng-f-abs-return` |
| Indicators | `weather.houston.temp_anomaly` × `finance.NG=F.abs_return` |
| n_obs | 388 |
| r | -0.3698377627214562 |
| Best lag | -4 (days) |
| perm_p | 0.015968063872255488 |
| Bonferroni | 0.33532934131736525 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 5.5, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.temp_anomaly` (configured analysis window); `finance.NG=F.abs_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.3698377627214562, n=388).

The best tested lag was -4 days with r=-0.40219346050475985.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NG=F**, hold 1d
- Entry: weather.houston.temp_anomaly rolling_zscore_20d > 1 at close -> long NG=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=49 hit_rate=1.0 avg_return=0.026715611369602554 excess=-0.004906312992270814 sharpe_like=9.06234429565739 max_dd=0.0
- OOS (war period): n=18 hit=1.0 avg=0.020263929705909622
- Actionability: 5.5
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
