# S-0012

| Field | Value |
|---|---|
| Mission id | `S-0012` |
| Folder | `20260920-216-weather-oklahoma-city-temp-anomaly_x_finance-zc-f-log-return` |
| Indicators | `weather.oklahoma_city.temp_anomaly` × `finance.ZC=F.log_return` |
| n_obs | 387 |
| r | 0.022198301123478432 |
| Best lag | -9 (days) |
| perm_p | 0.007984031936127744 |
| Bonferroni | 0.16766467065868262 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.62, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.oklahoma_city.temp_anomaly` (configured analysis window); `finance.ZC=F.log_return` (configured analysis window) |

**Verdict:** supported (Pearson r=0.022198301123478432, n=387).

The best tested lag was -9 days with r=0.151469791277646.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long ZC=F**, hold 1d
- Entry: weather.oklahoma_city.temp_anomaly rolling_zscore_20d > 1 at close -> long ZC=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=0.5 avg_return=0.003622999323379674 excess=0.003137896142097484 sharpe_like=1.676499736716327 max_dd=-0.07687976861259505
- OOS (war period): n=22 hit=0.5454545454545454 avg=0.004094204863440471
- Actionability: 7.62
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
