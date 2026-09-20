# R2-0025

| Field | Value |
|---|---|
| Mission id | `R2-0025` |
| Folder | `20260920-148-weather-rotterdam-temp-anomaly_x_finance-ttf-f-log-return` |
| Indicators | `weather.rotterdam.temp_anomaly` × `finance.TTF=F.log_return` |
| n_obs | 388 |
| r | 0.02597475187252149 |
| Best lag | 2 (days) |
| perm_p | 0.013972055888223553 |
| Bonferroni | 0.2934131736526946 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 0.79, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.rotterdam.temp_anomaly` (configured analysis window); `finance.TTF=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.02597475187252149, n=388).

The best tested lag was 2 days with r=0.12905487998672455.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long TTF=F**, hold 2d
- Entry: weather.rotterdam.temp_anomaly rolling_zscore_20d > 1 at close -> long TTF=F next session
- Exit: close after 2 trading days (no overlapping entries)
- n_trades=39 hit_rate=0.5128205128205128 avg_return=0.004637026543299037 excess=-0.0002789082156467457 sharpe_like=0.40623666925554247 max_dd=-0.21407310649949485
- OOS (war period): n=12 hit=0.5 avg=-0.001390129403462309
- Actionability: 0.79
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
