# R2-0049

| Field | Value |
|---|---|
| Mission id | `R2-0049` |
| Folder | `20260920-165-weather-oklahoma-city-temp-anomaly_x_finance-zw-f-log-return` |
| Indicators | `weather.oklahoma_city.temp_anomaly` × `finance.ZW=F.log_return` |
| n_obs | 387 |
| r | 0.002139090862873883 |
| Best lag | -6 (days) |
| perm_p | 0.624750499001996 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.96, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.oklahoma_city.temp_anomaly` (configured analysis window); `finance.ZW=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=0.002139090862873883, n=387).

The best tested lag was -6 days with r=-0.07796329178286858.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZW=F**, hold 1d
- Entry: weather.oklahoma_city.temp_anomaly rolling_zscore_20d > 1 at close -> long ZW=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.5555555555555556 avg_return=0.0035871447266806016 excess=0.002677806301975112 sharpe_like=1.3600873398177835 max_dd=-0.05852906169427208
- OOS (war period): n=22 hit=0.6363636363636364 avg=0.005128818471421447
- Actionability: 7.96
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
