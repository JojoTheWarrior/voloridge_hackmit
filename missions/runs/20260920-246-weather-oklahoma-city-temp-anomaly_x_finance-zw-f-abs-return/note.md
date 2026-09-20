# R2-0148

| Field | Value |
|---|---|
| Mission id | `R2-0148` |
| Folder | `20260920-246-weather-oklahoma-city-temp-anomaly_x_finance-zw-f-abs-return` |
| Indicators | `weather.oklahoma_city.temp_anomaly` × `finance.ZW=F.abs_return` |
| n_obs | 387 |
| r | 0.0389118948595419 |
| Best lag | -9 (days) |
| perm_p | 0.35528942115768464 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.5, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.oklahoma_city.temp_anomaly` (configured analysis window); `finance.ZW=F.abs_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0389118948595419, n=387).

The best tested lag was -9 days with r=0.13818721747901033.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZW=F**, hold 1d
- Entry: weather.oklahoma_city.temp_anomaly rolling_zscore_20d > 1 at close -> long ZW=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=1.0 avg_return=0.015159146990485931 excess=0.002383133914446018 sharpe_like=8.842780144663829 max_dd=0.0
- OOS (war period): n=22 hit=1.0 avg=0.014575660764752595
- Actionability: 7.5
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
