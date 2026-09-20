# R2-0035

| Field | Value |
|---|---|
| Mission id | `R2-0035` |
| Folder | `20260920-156-weather-houston-temp-anomaly_x_finance-ng-f-log-return` |
| Indicators | `weather.houston.temp_anomaly` × `finance.NG=F.log_return` |
| n_obs | 388 |
| r | 0.013099582338329032 |
| Best lag | 3 (days) |
| perm_p | 0.03992015968063872 |
| Bonferroni | 0.8383233532934131 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 3.17, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.houston.temp_anomaly` (configured analysis window); `finance.NG=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.013099582338329032, n=388).

The best tested lag was 3 days with r=0.18059925540987634.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long NG=F**, hold 3d
- Entry: weather.houston.temp_anomaly rolling_zscore_20d > 1 at close -> long NG=F next session
- Exit: close after 3 trading days (no overlapping entries)
- n_trades=40 hit_rate=0.475 avg_return=0.00013215473054873638 excess=-0.0013132397364054263 sharpe_like=0.01346359446998348 max_dd=-0.4273085862580063
- OOS (war period): n=13 hit=0.5384615384615384 avg=0.010832604285129154
- Actionability: 3.17
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
