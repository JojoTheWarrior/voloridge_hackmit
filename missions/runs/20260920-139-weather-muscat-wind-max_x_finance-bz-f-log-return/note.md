# R2-0011

| Field | Value |
|---|---|
| Mission id | `R2-0011` |
| Folder | `20260920-139-weather-muscat-wind-max_x_finance-bz-f-log-return` |
| Indicators | `weather.muscat.wind_max` × `finance.BZ=F.log_return` |
| n_obs | 388 |
| r | -0.04344401741448076 |
| Best lag | 6 (days) |
| perm_p | 0.93812375249501 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 7.34, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.muscat.wind_max` (configured analysis window); `finance.BZ=F.log_return` (configured analysis window) |

**Verdict:** not supported (Pearson r=-0.04344401741448076, n=388).

The best tested lag was 6 days with r=-0.07935739143477778.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long BZ=F**, hold 6d
- Entry: weather.muscat.wind_max rolling_zscore_20d > 1 at close -> long BZ=F next session
- Exit: close after 6 trading days (no overlapping entries)
- n_trades=29 hit_rate=0.5862068965517241 avg_return=0.027730523759673262 excess=0.018493861060720016 sharpe_like=1.9703559657569005 max_dd=-0.2116487530868726
- OOS (war period): n=12 hit=0.6666666666666666 avg=0.062280031307847455
- Actionability: 7.34
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
