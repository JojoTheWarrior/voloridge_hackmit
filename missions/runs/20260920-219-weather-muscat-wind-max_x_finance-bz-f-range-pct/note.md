# R2-0108

| Field | Value |
|---|---|
| Mission id | `R2-0108` |
| Folder | `20260920-219-weather-muscat-wind-max_x_finance-bz-f-range-pct` |
| Indicators | `weather.muscat.wind_max` × `finance.BZ=F.range_pct` |
| n_obs | 388 |
| r | 0.0903703777964566 |
| Best lag | -10 (days) |
| perm_p | 0.11776447105788423 |
| Bonferroni | 1.0 |
| pre/post Δr |  |
| Fisher p |  |
| Scores | {'validity': 0, 'interestingness': 2.0, 'unexpectedness': 2.0, 'actionability': 10.0, 'supported_prob': 0.0, 'judge_model': 'heuristic'} |
| Data sources | `weather.muscat.wind_max` (configured analysis window); `finance.BZ=F.range_pct` (configured analysis window) |

**Verdict:** supported (Pearson r=0.0903703777964566, n=388).

The best tested lag was -10 days with r=0.21623187555556325.

This association is descriptive, not causal; seasonality, common shocks, and multiple testing remain possible confounders.

## Trade idea (Round 2 rubric)

- **long BZ=F**, hold 1d
- Entry: weather.muscat.wind_max rolling_zscore_20d > 1 at close -> long BZ=F next session
- Exit: close after 1 trading days (no overlapping entries)
- n_trades=54 hit_rate=1.0 avg_return=0.04111094215206769 excess=0.002169638184887343 sharpe_like=9.606921724684433 max_dd=0.0
- OOS (war period): n=22 hit=1.0 avg=0.06425509975309575
- Actionability: 10.0
- Caveats: Backtest on daily closes, no costs/slippage; few independent regimes; signal and target may share the war as common cause.
